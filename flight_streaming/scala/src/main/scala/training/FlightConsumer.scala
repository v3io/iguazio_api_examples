package training

import com.typesafe.config.{Config, ConfigFactory}
import io.iguaz.v3io.spark.streaming.{RecordAndMetadata, StringDecoder}
import org.apache.spark.sql.{SaveMode, SparkSession}
import org.apache.spark.streaming.v3io.V3IOUtils
import org.apache.spark.streaming.{Seconds, StreamingContext}


object FlightConsumer {

  implicit val config: Config = ConfigFactory.load()

  val appName: String = config.getString("application.name")
  val batchDurationSecs: Int = config.getInt("application.batchDuration")
  val inContainerId:String = config.getString("input.containerId")
  val topic: String = config.getString("input.topic")
  val topicsNames = Set(topic)
  val outContainerId:String = config.getString("output.containerId")
  val outputDataPath: String = config.getString("output.data")


  def main(args: Array[String]): Unit = {

    val spark = SparkSession
      .builder()
      .appName(appName)
      .getOrCreate()

    val ssc: StreamingContext = new StreamingContext(spark.sparkContext, Seconds(batchDurationSecs))

    val containerPropertiesMap = Map("container-id" -> inContainerId)

    val stream = {
      val messageHandler = (rmd: RecordAndMetadata[String]) => rmd.payload()
      V3IOUtils.createDirectStream[String, StringDecoder, String](
        ssc,
        containerPropertiesMap,
        topicsNames,
        messageHandler)
    }

    stream.foreachRDD(rdd => {
      if (!rdd.isEmpty()) {
        val df = spark.read.json(rdd)
        df.write
          .format("parquet")
          .mode(SaveMode.Overwrite)
          .option("container-id", outContainerId)
          .save(outputDataPath)
      }
    })

    ssc.start()
    ssc.awaitTermination()
  }
}
