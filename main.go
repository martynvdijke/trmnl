package main

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// Version is set at build time via -ldflags "-X main.Version=...".
var Version = "dev"

type config struct {
	immichURL    string
	immichAPIKey string
	port         string
}

func loadConfig() config {
	cfg := config{
		immichURL:    os.Getenv("IMMICH_URL"),
		immichAPIKey: os.Getenv("IMMICH_API_KEY"),
		port:         os.Getenv("PORT"),
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
	return cfg
}

func main() {
	cfg := loadConfig()
	client := &immichProxy{
		baseURL: strings.TrimRight(cfg.immichURL, "/"),
		apiKey:  cfg.immichAPIKey,
		http:    &http.Client{Timeout: 30 * time.Second},
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", handleHealthz)
	mux.HandleFunc("GET /api/trmnl/photo/{id}", client.handlePhoto)

	addr := ":" + cfg.port
	log.Printf("trmnl-immich %s listening on %s", Version, addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatal(err)
	}
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

// immichProxy proxies authenticated Immich asset bytes so the TRMNL device
// can render photos without holding an Immich API key.
type immichProxy struct {
	baseURL string
	apiKey  string
	http    *http.Client
}

func (p *immichProxy) handlePhoto(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if id == "" {
		writeError(w, http.StatusBadRequest, "missing photo id")
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
