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

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.spark.sql.SQLContext;
import org.apache.spark.sql.SparkSession;
import org.apache.spark.streaming.Duration;
import org.apache.spark.streaming.api.java.JavaDStream;
import org.apache.spark.streaming.api.java.JavaInputDStream;
import org.apache.spark.streaming.api.java.JavaStreamingContext;
import org.apache.spark.streaming.kafka010.ConsumerStrategies;
import org.apache.spark.streaming.kafka010.KafkaUtils;
import org.apache.spark.streaming.kafka010.LocationStrategies;

import com.iguazio.bo.Car;
import com.iguazio.function.KVIngestionVoidFunction;
import com.iguazio.function.StreamCarFunction;

public class KafkaToKvIngestionDriver implements Serializable {

	/**
	 * 
	 */
	private static final long serialVersionUID = 1L;

	private SparkSession session;
	private JavaStreamingContext jsc;
	private SQLContext sqlContext;

	public KafkaToKvIngestionDriver() {

		init();
	}

	public void init() {

		this.jsc = new JavaStreamingContext("local[*]", "IguazioApiTest", new Duration(5000));
		// this.session =
		// SparkSession.builder().master("local[*]").appName("IguazioApiTest").getOrCreate();

	}

	public static void main(String[] args) throws InterruptedException {
		KafkaToKvIngestionDriver driver = new KafkaToKvIngestionDriver();
		driver.run();

	}

	public void run() throws InterruptedException {
		Collection<String> topics = Arrays.asList("cars");

		Map<String, Object> kafkaParams = new HashMap<>();
		kafkaParams.put("bootstrap.servers", "0.0.0.0:32773");
		kafkaParams.put("auto.commit.interval.ms", "1000");
		kafkaParams.put("auto.offset.reset", "earliest");
		kafkaParams.put("session.timeout.ms", "30000");

		kafkaParams.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
				"org.apache.kafka.common.serialization.StringDeserializer");
		kafkaParams.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
				"org.apache.kafka.common.serialization.StringDeserializer");
		kafkaParams.put("group.id", "grp1");
		JavaInputDStream<ConsumerRecord<String, String>> stream = KafkaUtils.createDirectStream(jsc,
				LocationStrategies.PreferConsistent(),
				ConsumerStrategies.<String, String>Subscribe(topics, kafkaParams));

		JavaDStream<Car> carsStream = stream.map(new StreamCarFunction());

		carsStream.foreachRDD(new KVIngestionVoidFunction());
		jsc.start();
		jsc.awaitTermination();

	}

}
