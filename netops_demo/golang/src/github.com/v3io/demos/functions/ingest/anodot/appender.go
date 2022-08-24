/*
Copyright 2017 Iguazio Systems Ltd.

Licensed under the Apache License, Version 2.0 (the "License") with
an addition restriction as set forth herein. You may not use this
file except in compliance with the License. You may obtain a copy of
the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
implied. See the License for the specific language governing
permissions and limitations under the License.

In addition, you may not use the software for any purposes that are
illegal under applicable law, and the grant of the foregoing license
under the Apache 2.0 license is conditioned upon your compliance with
such restriction.
*/
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
