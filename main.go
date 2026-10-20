package main

import (
	"crypto/subtle"
	"encoding/json"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

// Version is set at build time via -ldflags "-X main.Version=...".
var Version = "dev"

type config struct {
	immichURL    string
	immichAPIKey string
	port         string
	host         string
	proxyToken   string
}

func loadConfig() config {
	cfg := config{
		immichURL:    os.Getenv("IMMICH_URL"),
		immichAPIKey: os.Getenv("IMMICH_API_KEY"),
		port:         os.Getenv("PORT"),
		host:         os.Getenv("HOST"),
		proxyToken:   firstNonEmpty(os.Getenv("TRMNL_PROXY_TOKEN"), os.Getenv("PROXY_TOKEN")),
	}
	if cfg.immichURL == "" {
		log.Fatal("IMMICH_URL environment variable is required")
	}
	if cfg.immichAPIKey == "" {
		log.Fatal("IMMICH_API_KEY environment variable is required")
	}
	if cfg.port == "" {
		cfg.port = "8080"
	}
	if cfg.host == "" {
		// Without a token only the local machine may reach the proxy; an
		// operator who wants LAN access must set TRMNL_PROXY_TOKEN.
		if cfg.proxyToken == "" {
			cfg.host = "127.0.0.1"
		} else {
			cfg.host = "0.0.0.0"
		}
	}
	return cfg
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if strings.TrimSpace(v) != "" {
			return strings.TrimSpace(v)
		}
	}
	return ""
}

func main() {
	cfg := loadConfig()
	client := &immichProxy{
		baseURL: strings.TrimRight(cfg.immichURL, "/"),
		apiKey:  cfg.immichAPIKey,
		http:    &http.Client{Timeout: 30 * time.Second},
	}

	addr := net.JoinHostPort(cfg.host, cfg.port)
	log.Printf("trmnl-immich %s listening on %s", Version, addr)
	if err := http.ListenAndServe(addr, newMux(cfg, client)); err != nil {
		log.Fatal(err)
	}
}

func newMux(cfg config, proxy *immichProxy) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", handleHealthz)
	var photo http.Handler = http.HandlerFunc(proxy.handlePhoto)
	if cfg.proxyToken != "" {
		photo = requireProxyToken(cfg.proxyToken, rateLimit(120, time.Minute, photo))
	}
	mux.Handle("GET /api/trmnl/photo/{id}", photo)
	return mux
}

func handleHealthz(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok"))
}

func writeError(w http.ResponseWriter, status int, msg string) {
	log.Printf("error: %s (status %d)", msg, status)
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": msg})
}

// requireProxyToken accepts `Authorization: Bearer <token>`, `X-Proxy-Token`,
// or `?token=` so e-ink devices and the TRMNL server can both authenticate.
func requireProxyToken(token string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		presented := ""
		if auth := r.Header.Get("Authorization"); strings.HasPrefix(auth, "Bearer ") {
			presented = strings.TrimSpace(strings.TrimPrefix(auth, "Bearer "))
		}
		if presented == "" {
			presented = r.Header.Get("X-Proxy-Token")
		}
		if presented == "" {
			presented = r.URL.Query().Get("token")
		}
		if subtle.ConstantTimeCompare([]byte(presented), []byte(token)) != 1 {
			w.Header().Set("WWW-Authenticate", `Bearer realm="trmnl-immich"`)
			writeError(w, http.StatusUnauthorized, "unauthorized")
			return
		}
		next.ServeHTTP(w, r)
	})
}

type rateEntry struct {
	window time.Time
	count  int
}

// rateLimit applies a fixed-window per-IP budget. The proxy only serves image
// bytes, so a modest limit is enough to stop accidental loops and abuse.
func rateLimit(limit int, window time.Duration, next http.Handler) http.Handler {
	var mu sync.Mutex
	hits := map[string]*rateEntry{}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ip := r.RemoteAddr
		if host, _, err := net.SplitHostPort(r.RemoteAddr); err == nil {
			ip = host
		}
		now := time.Now()
		mu.Lock()
		entry := hits[ip]
		if entry == nil || now.Sub(entry.window) >= window {
			entry = &rateEntry{window: now}
			hits[ip] = entry
		}
		entry.count++
		exceeded := entry.count > limit
		mu.Unlock()
		if exceeded {
			w.Header().Set("Retry-After", "60")
			writeError(w, http.StatusTooManyRequests, "too many requests")
			return
		}
		next.ServeHTTP(w, r)
	})
}

// immichProxy proxies authenticated Immich asset bytes so the TRMNL device
// can render photos without holding an Immich API key.
type immichProxy struct {
	baseURL string
	apiKey  string
	http    *http.Client
}

// assetIDPattern only permits characters Immich uses in UUIDs. It rejects
// slashes, dots, percent escapes, and anything that could escape the asset
// path before the value is URL-escaped.
var assetIDPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`)

func validAssetID(id string) bool {
	return assetIDPattern.MatchString(id)
}

func (p *immichProxy) handlePhoto(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "missing photo id")
		return
	}
	if !validAssetID(id) {
		writeError(w, http.StatusBadRequest, "invalid photo id")
		return
	}

	u := p.baseURL + "/api/assets/" + url.PathEscape(id) + "/thumbnail"
	req, err := http.NewRequestWithContext(r.Context(), http.MethodGet, u, nil)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	q := req.URL.Query()
	q.Set("size", "preview")
	req.URL.RawQuery = q.Encode()
	req.Header.Set("x-api-key", p.apiKey)
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "trmnl-immich/"+Version)

	resp, err := p.http.Do(req)
	if err != nil {
		writeError(w, http.StatusBadGateway, err.Error())
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		writeError(w, resp.StatusCode, "upstream returned non-200")
		return
	}
	if ct := resp.Header.Get("Content-Type"); ct != "" {
		w.Header().Set("Content-Type", ct)
	}
	w.Header().Set("Cache-Control", "public, max-age=86400")
	if _, err := io.Copy(w, resp.Body); err != nil {
		log.Printf("handlePhoto: copy: %v", err)
	}
}
