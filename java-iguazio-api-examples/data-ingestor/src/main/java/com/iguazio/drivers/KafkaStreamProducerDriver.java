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

import java.util.Properties;
import java.util.Random;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;

public class KafkaStreamProducerDriver {

	private static Properties props = new Properties();
	private static KafkaProducer<String, String> kafkaProducer;

	public static void main(String[] args) {
		KafkaStreamProducerDriver driver = new KafkaStreamProducerDriver();
		driver.init();
		driver.run();

	}

	public void init() {
		props.put("bootstrap.servers", "0.0.0.0:32773");
		props.put("acks", "all");
		props.put("retries", 0);
		props.put("batch.size", 1500);
		props.put("linger.ms", 1);
		props.put("buffer.memory", 33554432);
		props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
		props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
		kafkaProducer = new KafkaProducer<String, String>(props);

	}

	public void run() {

		double[] downtown = { -0.1195, 51.5033 };
		double[] westminster = { -0.1357, 51.4975 };
		double[] oxfordSt = { -0.1410, 51.5154 };
		double[] heathrow = { -0.4543, 51.4700 };
		double[] heathrowParking = { -0.4473, 51.4599 };
		double[] gatwick = { 0.1821, 51.1537 };
		double[] canaryWharf = { -0.0235, 51.5054 };
		double[][] locations = { downtown, westminster, oxfordSt, heathrow, heathrowParking, gatwick, canaryWharf };
		String[] driverStatus = { "busy", "available", "passenger" };

		/**
		 * producing random batches of data every 5 second.
		 */
		Random random = new Random();

		for (int x = 0; x <= 1000; x++) {
			int location = random.nextInt(7);
			int radius = random.nextInt(6);
			for (int i = 0; i <= 300; i++) {
				int driver = random.nextInt(5001);

				double longitude = locations[location][0] + random.nextDouble() * (-radius - radius) + -radius;
				double latitude = locations[location][1] + random.nextDouble() * (-radius - radius) + -radius;
				kafkaProducer.send(new ProducerRecord<String, String>("cars", Integer.toString(driver),
						driver + "," + System.currentTimeMillis() + "," + longitude + "," + latitude + ","
								+ driverStatus[random.nextInt(3)]));
			}
			try {
				Thread.sleep(5000);
			} catch (InterruptedException e) {
				e.printStackTrace();
				kafkaProducer.close();
			}
			System.out.println("batch write success");
		}

	}

}
