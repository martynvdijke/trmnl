package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestNewMuxRequiresTokenWhenConfigured(t *testing.T) {
	server := fakeImmich(t)
	defer server.Close()
	mux := newMux(config{proxyToken: "secret"}, newTestProxy(t, server))

	for _, tc := range []struct {
		name   string
		token  string
		header string
		want   int
	}{
		{"missing", "", "", http.StatusUnauthorized},
		{"wrong", "nope", "Authorization", http.StatusUnauthorized},
		{"bearer", "secret", "Authorization", http.StatusOK},
		{"x-proxy", "secret", "X-Proxy-Token", http.StatusOK},
	} {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/api/trmnl/photo/asset-1", nil)
			switch tc.header {
			case "Authorization":
				req.Header.Set("Authorization", "Bearer "+tc.token)
			case "X-Proxy-Token":
				req.Header.Set("X-Proxy-Token", tc.token)
			}
			rec := httptest.NewRecorder()
			mux.ServeHTTP(rec, req)
			if rec.Code != tc.want {
				t.Fatalf("got %d, want %d (%s)", rec.Code, tc.want, rec.Body.String())
			}
		})
	}
}

func TestNewMuxAllowsQueryToken(t *testing.T) {
	server := fakeImmich(t)
	defer server.Close()
	mux := newMux(config{proxyToken: "secret"}, newTestProxy(t, server))
	req := httptest.NewRequest(http.MethodGet, "/api/trmnl/photo/asset-1?token=secret", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("got %d, want 200", rec.Code)
	}
}

func TestNewMuxWithoutTokenLeavesPhotoOpenOnLoopback(t *testing.T) {
	server := fakeImmich(t)
	defer server.Close()
	mux := newMux(config{}, newTestProxy(t, server))
	req := httptest.NewRequest(http.MethodGet, "/api/trmnl/photo/asset-1", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("got %d, want 200", rec.Code)
	}
}

func TestValidAssetID(t *testing.T) {
	for _, id := range []string{"asset-1", "0f8fad5b-d9cb-469f-a165-70867728950e", "abc_123"} {
		if !validAssetID(id) {
			t.Errorf("expected %q to be valid", id)
		}
	}
	for _, id := range []string{"", "../etc/passwd", "a/b", "a.b", "a%2f", "a b", "a?x=1"} {
		if validAssetID(id) {
			t.Errorf("expected %q to be rejected", id)
		}
	}
}

func TestRateLimit(t *testing.T) {
	h := rateLimit(2, time.Minute, http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	for i := 0; i < 2; i++ {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
		if rec.Code != http.StatusOK {
			t.Fatalf("request %d: got %d", i+1, rec.Code)
		}
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	if rec.Code != http.StatusTooManyRequests {
		t.Fatalf("got %d, want 429", rec.Code)
	}
}
