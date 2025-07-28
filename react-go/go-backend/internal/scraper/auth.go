package scraper

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/dghubble/oauth1"
)

const TokenFile = "discogs_token.json"

type TokenData struct {
	Token  string `json:"token"`
	Secret string `json:"secret"`
}

// LoadTokens loads OAuth tokens from file
func LoadTokens() (*TokenData, error) {
	if _, err := os.Stat(TokenFile); os.IsNotExist(err) {
		return nil, nil
	}

	data, err := os.ReadFile(TokenFile)
	if err != nil {
		return nil, fmt.Errorf("failed to read token file: %w", err)
	}

	var tokens TokenData
	if err := json.Unmarshal(data, &tokens); err != nil {
		return nil, fmt.Errorf("failed to unmarshal tokens: %w", err)
	}

	return &tokens, nil
}

// SaveTokens saves OAuth tokens to file
func SaveTokens(token, secret string) error {
	tokens := TokenData{
		Token:  token,
		Secret: secret,
	}

	data, err := json.Marshal(tokens)
	if err != nil {
		return fmt.Errorf("failed to marshal tokens: %w", err)
	}

	if err := os.WriteFile(TokenFile, data, 0600); err != nil {
		return fmt.Errorf("failed to write token file: %w", err)
	}

	return nil
}

// AuthenticateClient performs OAuth 1.0 authentication with Discogs
func AuthenticateClient(consumerKey, consumerSecret string) (*oauth1.Config, *oauth1.Token, error) {
	config := oauth1.NewConfig(consumerKey, consumerSecret)
	config.Endpoint = oauth1.Endpoint{
		RequestTokenURL: "https://api.discogs.com/oauth/request_token",
		AuthorizeURL:    "https://www.discogs.com/oauth/authorize",
		AccessTokenURL:  "https://api.discogs.com/oauth/access_token",
	}

	// First try to use tokens from environment variables
	discogsCredsEnv := os.Getenv("DISCOGS_CREDS")
	if discogsCredsEnv != "" {
		var envCreds map[string]string
		if err := json.Unmarshal([]byte(discogsCredsEnv), &envCreds); err == nil {
			if token, ok := envCreds["token"]; ok {
				if secret, ok := envCreds["secret"]; ok {
					fmt.Println("Using Discogs tokens from environment variables")
					oauthToken := &oauth1.Token{
						Token:       token,
						TokenSecret: secret,
					}
					return config, oauthToken, nil
				}
			}
		}
	}

	// Try to load existing tokens from file
	tokens, err := LoadTokens()
	if err != nil {
		return nil, nil, fmt.Errorf("failed to load tokens: %w", err)
	}

	if tokens != nil {
		// Use existing tokens
		token := &oauth1.Token{
			Token:       tokens.Token,
			TokenSecret: tokens.Secret,
		}
		return config, token, nil
	}

	// Perform OAuth flow
	requestToken, requestSecret, err := config.RequestToken()
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get request token: %w", err)
	}

	authorizationURL, err := config.AuthorizationURL(requestToken)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get authorization URL: %w", err)
	}

	fmt.Printf("Please visit this URL to authorize: %s\n", authorizationURL.String())
	fmt.Print("Enter the verifier code: ")

	reader := bufio.NewReader(os.Stdin)
	verifier, err := reader.ReadString('\n')
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read verifier: %w", err)
	}
	verifier = strings.TrimSpace(verifier)

	accessToken, accessSecret, err := config.AccessToken(requestToken, requestSecret, verifier)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get access token: %w", err)
	}

	// Save tokens for future use
	if err := SaveTokens(accessToken, accessSecret); err != nil {
		return nil, nil, fmt.Errorf("failed to save tokens: %w", err)
	}

	token := &oauth1.Token{
		Token:       accessToken,
		TokenSecret: accessSecret,
	}

	return config, token, nil
}
