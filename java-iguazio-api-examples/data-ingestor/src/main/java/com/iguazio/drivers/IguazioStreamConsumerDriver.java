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
package com.iguazio.drivers;
import java.io.IOException;
import java.io.Serializable;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.apache.spark.streaming.api.java.JavaInputDStream;
import org.apache.spark.streaming.api.java.JavaStreamingContext;
import org.apache.spark.streaming.v3io.V3IOUtils;

import com.iguazio.function.IguazioStreamVoidFunction;

import io.iguaz.v3io.daemon.client.api.consts.ConfigProperty;
import io.iguaz.v3io.spark.streaming.StringDecoder;

public class IguazioStreamConsumerDriver implements Serializable {

	/**
	 * 
	 */
	private static final long serialVersionUID = 1L;

	private JavaStreamingContext jsc;

	public IguazioStreamConsumerDriver() {

		init();
	}

	public void init() {

		this.jsc = new JavaStreamingContext("local[*]", "IguazioApiTest",
				new org.apache.spark.streaming.Duration(5000));

	}

	public static void main(String[] args) throws InterruptedException, IOException {
		IguazioStreamConsumerDriver driver = new IguazioStreamConsumerDriver();
		driver.run();

	}

	public void run() throws InterruptedException, IOException {
		Set<String> topics = new HashSet<>();
		topics.add("/cars-stream");

		Map<String, String> hashMap = new HashMap<>();

		hashMap.put(ConfigProperty.CONTAINER_ID, "1");

		JavaInputDStream<String> stream = V3IOUtils.createDirectStream(jsc, String.class, StringDecoder.class, hashMap,
				topics);

		stream.foreachRDD(new IguazioStreamVoidFunction());

		jsc.start();
		jsc.awaitTermination();

	}

}
