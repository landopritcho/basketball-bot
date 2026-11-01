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

func (s ScrapingClient) Scrape(url string) (*http.Response, error) {
	req, err := http.NewRequestWithContext(
		context.Background(), http.MethodGet, url, nil,
	)
	if err != nil {
		return &http.Response{}, err
	}
	req.Header.Set("User-Agent", s.UserAgent)

	resp, err := s.HttpClient.Do(req)
	if err != nil {
		return &http.Response{}, err
	}

	if resp.StatusCode < 200 || resp.StatusCode > 299 {
		return &http.Response{}, fmt.Errorf("unsuccessful http request for %s", url)
	}

	return resp, nil
}

func (s ScrapingClient) SetUserAgent(name string) {
	s.UserAgent = strings.TrimSpace(name)
}
