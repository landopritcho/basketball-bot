// Package http contains the client for running web scraping functions.
package http

import (
	"context"
	"fmt"
	"net/http"
	"strings"
	"time"
)

const (
	defaultUserAgent = "BasketballBot/1.0"
	defaultTimeout   = 20 * time.Second
)

type ScrapingClient struct {
	HttpClient *http.Client
	UserAgent  string
}

func NewClient() ScrapingClient {
	client := &http.Client{Timeout: defaultTimeout}
	return ScrapingClient{
		HttpClient: client,
		UserAgent:  defaultUserAgent,
	}
}

func (s ScrapingClient) Scrape(url string, useUserAgent *bool) (*http.Response, error) {
	req, err := http.NewRequestWithContext(
		context.Background(), http.MethodGet, url, nil,
	)
	if err != nil {
		return &http.Response{}, err
	}
	if useUserAgent != nil && *useUserAgent {
		req.Header.Set("User-Agent", "BasketballBot/1.0")
	} else {
		req.Header.Set("User-Agent", "")
	}

	resp, err := s.HttpClient.Do(req)
	if err != nil {
		return &http.Response{}, err
	}

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return nil, fmt.Errorf("unsuccessful http request for %s: %s", url, resp.Status)
	}

	return resp, nil
}

func (s ScrapingClient) SetUserAgent(name string) {
	s.UserAgent = strings.TrimSpace(name)
}
