package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"
)

// ──────────────────────────────────────────────
// Config
// ──────────────────────────────────────────────

type Config struct {
	Port         string
	FlaskURL     string
	RedisAddr    string
	APIKey       string
	RateLimit    int
	RateWindow   time.Duration
	CacheTTL     time.Duration
}

func loadConfig() Config {
	return Config{
		Port:       getEnv("GATEWAY_PORT", "8080"),
		FlaskURL:   getEnv("FLASK_URL", "http://flask-app:5000"),
		RedisAddr:  getEnv("REDIS_ADDR", "redis:6379"),
		APIKey:     getEnv("API_KEY", ""),
		RateLimit:  getEnvInt("RATE_LIMIT", 30),
		RateWindow: time.Minute,
		CacheTTL:   30 * time.Second,
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	var n int
	fmt.Sscanf(v, "%d", &n)
	if n <= 0 {
		return fallback
	}
	return n
}

// ──────────────────────────────────────────────
// Rate Limiter (in-memory fallback + Redis)
// ──────────────────────────────────────────────

type RateLimiter struct {
	rdb        *redis.Client
	limit      int
	window     time.Duration
	mu         sync.Mutex
	memCounts  map[string]int
	memResets  map[string]time.Time
	useRedis   bool
}

func NewRateLimiter(rdb *redis.Client, limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		rdb:       rdb,
		limit:     limit,
		window:    window,
		memCounts: make(map[string]int),
		memResets: make(map[string]time.Time),
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Printf("[gateway] Redis unavailable (%v), using in-memory rate limiting", err)
		rl.useRedis = false
	} else {
		rl.useRedis = true
		log.Println("[gateway] Redis connected for rate limiting & caching")
	}
	return rl
}

func (rl *RateLimiter) Allow(key string) bool {
	if rl.useRedis {
		return rl.allowRedis(key)
	}
	return rl.allowMem(key)
}

func (rl *RateLimiter) allowRedis(key string) bool {
	ctx := context.Background()
	rk := "rl:" + key
	count, err := rl.rdb.Incr(ctx, rk).Result()
	if err != nil {
		return true // fail open
	}
	if count == 1 {
		rl.rdb.Expire(ctx, rk, rl.window)
	}
	return int(count) <= rl.limit
}

func (rl *RateLimiter) allowMem(key string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	if reset, ok := rl.memResets[key]; !ok || now.After(reset) {
		rl.memCounts[key] = 1
		rl.memResets[key] = now.Add(rl.window)
		return true
	}
	rl.memCounts[key]++
	return rl.memCounts[key] <= rl.limit
}

// ──────────────────────────────────────────────
// Cache (Redis-backed)
// ──────────────────────────────────────────────

type Cache struct {
	rdb *redis.Client
	ttl time.Duration
	ok  bool
}

func NewCache(rdb *redis.Client, ttl time.Duration) *Cache {
	c := &Cache{rdb: rdb, ttl: ttl}
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	c.ok = rdb.Ping(ctx).Err() == nil
	return c
}

func (c *Cache) Get(key string) ([]byte, bool) {
	if !c.ok {
		return nil, false
	}
	val, err := c.rdb.Get(context.Background(), "cache:"+key).Bytes()
	if err != nil {
		return nil, false
	}
	return val, true
}
