package anodot

import (
	"net/http"
	"time"
	"fmt"
	"encoding/json"
	"bytes"
	"io/ioutil"

	"github.com/nuclio/logger"
)

type Metric struct {
	Properties map[string]interface{} `json:"properties,omitempty"`
	Tags map[string]interface{} `json:"tags,omitempty"`
	Timestamp uint64 `json:"timestamp,omitempty"`
	Value float64 `json:"value,omitempty"`
}

type Appender struct {
	logger logger.Logger
	httpClient *http.Client
	appendEndpoint string
}

func NewAppender(parentLogger logger.Logger, url string, token string) (*Appender, error) {
	return &Appender{
		logger: parentLogger.GetChild("anodot"),
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		appendEndpoint: fmt.Sprintf("%s/api/v1/metrics?token=%s&protocol=anodot20", url, token),
	}, nil
}

func (a *Appender) Append(metric []*Metric) error {
	serializedMetric, err := json.Marshal(metric)
	if err != nil {
		return err
	}

	response, err := a.httpClient.Post(a.appendEndpoint, "application/json", bytes.NewReader(serializedMetric))
	if err != nil {
		return err
	}

	responseBody, err := ioutil.ReadAll(response.Body)
	if err != nil {
		return err
	}

	a.logger.InfoWith("Got response",
		"url", a.appendEndpoint,
		"statusCode", response.StatusCode,
		"responseBody", string(responseBody))

	return nil
}
