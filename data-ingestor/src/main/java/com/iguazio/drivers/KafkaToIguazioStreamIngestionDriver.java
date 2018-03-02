package com.iguazio.drivers;

import java.io.IOException;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.spark.streaming.api.java.JavaDStream;
import org.apache.spark.streaming.api.java.JavaInputDStream;
import org.apache.spark.streaming.api.java.JavaStreamingContext;
import org.apache.spark.streaming.kafka010.ConsumerStrategies;
import org.apache.spark.streaming.kafka010.KafkaUtils;
import org.apache.spark.streaming.kafka010.LocationStrategies;

import com.iguazio.bo.Car;
import com.iguazio.function.StreamCarFunction;
import com.iguazio.function.StreamIngestionVoidFunction;

public class KafkaToIguazioStreamIngestionDriver implements Serializable {

	/**
	 * 
	 */
	private static final long serialVersionUID = 1L;

	private JavaStreamingContext jsc;

	public KafkaToIguazioStreamIngestionDriver() {

		init();
	}

	public void init() {

		this.jsc = new JavaStreamingContext("local[*]", "IguazioApiTest",
				new org.apache.spark.streaming.Duration(5000));

	}

	public static void main(String[] args) throws InterruptedException, IOException {
		KafkaToIguazioStreamIngestionDriver driver = new KafkaToIguazioStreamIngestionDriver();
		driver.run();

	}

	public void run() throws InterruptedException, IOException {
		Collection<String> topics = Arrays.asList("cars-new");

		Map<String, Object> kafkaParams = new HashMap<>();
		kafkaParams.put("bootstrap.servers", "172.17.0.3:9092");
		kafkaParams.put("auto.commit.interval.ms", "1000");
		kafkaParams.put("auto.offset.reset", "earliest");
		kafkaParams.put("session.timeout.ms", "30000");

		kafkaParams.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
				"org.apache.kafka.common.serialization.StringDeserializer");
		kafkaParams.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
				"org.apache.kafka.common.serialization.StringDeserializer");
		kafkaParams.put("group.id", "grp1");
		JavaInputDStream<ConsumerRecord<String, String>> inputStream = KafkaUtils.createDirectStream(jsc,
				LocationStrategies.PreferConsistent(),
				ConsumerStrategies.<String, String>Subscribe(topics, kafkaParams));

		JavaDStream<Car> carsStream = inputStream.map(new StreamCarFunction());

		carsStream.foreachRDD(new StreamIngestionVoidFunction());
		jsc.start();
		jsc.awaitTermination();

	}

}
