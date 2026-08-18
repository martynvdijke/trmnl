package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

const testKey = "test-api-key"

func fakeImmich(t *testing.T) *httptest.Server {
	t.Helper()
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("x-api-key") != testKey {
			t.Errorf("expected x-api-key %q, got %q", testKey, r.Header.Get("x-api-key"))
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		switch r.URL.Path {
		case "/api/assets/asset-1/thumbnail":
			if r.URL.Query().Get("size") != "preview" {
				t.Errorf("expected size=preview, got %q", r.URL.Query().Get("size"))
			}
			w.Header().Set("Content-Type", "image/webp")
			_, _ = w.Write([]byte("fake-thumbnail-bytes"))
		case "/api/assets/asset-404/thumbnail":
			http.Error(w, "not found", http.StatusNotFound)
		default:
			http.NotFound(w, r)
		}
	}))
}

func newTestProxy(t *testing.T, server *httptest.Server) *immichProxy {
	t.Helper()
	return &immichProxy{
		baseURL: server.URL,
		apiKey:  testKey,
		http:    server.Client(),
	}
}

func TestPhotoHandler(t *testing.T) {
	server := fakeImmich(t)
	defer server.Close()
	proxy := newTestProxy(t, server)

	req := httptest.NewRequest(http.MethodGet, "/api/trmnl/photo/asset-1", nil)
	req.SetPathValue("id", "asset-1")
	rec := httptest.NewRecorder()
	proxy.handlePhoto(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	if rec.Body.String() != "fake-thumbnail-bytes" {
		t.Errorf("unexpected body: %q", rec.Body.String())
	}
	if ct := rec.Header().Get("Content-Type"); ct != "image/webp" {
		t.Errorf("expected image/webp, got %q", ct)
	}
}

func TestPhotoHandlerMissingID(t *testing.T) {
	server := fakeImmich(t)
	defer server.Close()
	proxy := newTestProxy(t, server)

	req := httptest.NewRequest(http.MethodGet, "/api/trmnl/photo/", nil)
	req.SetPathValue("id", "")
	rec := httptest.NewRecorder()
	proxy.handlePhoto(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "missing photo id") {
		t.Errorf("unexpected body: %s", rec.Body.String())
	}
}

func TestPhotoHandlerUpstream404(t *testing.T) {
	server := fakeImmich(t)
	defer server.Close()
	proxy := newTestProxy(t, server)

	req := httptest.NewRequest(http.MethodGet, "/api/trmnl/photo/asset-404", nil)
	req.SetPathValue("id", "asset-404")
	rec := httptest.NewRecorder()
	proxy.handlePhoto(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 passthrough, got %d", rec.Code)
	}
}
