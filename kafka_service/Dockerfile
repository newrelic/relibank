# Start from the base Bitnami Kafka image
FROM bitnamilegacy/kafka:3.5

# ADD https://download.newrelic.com/newrelic/java-agent/newrelic-agent/current/newrelic-java.zip /tmp/newrelic-java.zip
# RUN unzip /tmp/newrelic-java.zip -d /opt/
# RUN rm /tmp/newrelic-java.zip

# ENV KAFKA_JVM_OPTS="-javaagent:/opt/newrelic/newrelic.jar"

# ENV NEW_RELIC_APP_NAME="${APP_NAME} - Kafka Service"

# CMD 
# sudo yum -q makecache -y --disablerepo='*' -- 
# sudo yum install nri-kafka
# cd /etc/newrelic-infra/integrations.d
# sudo cp kafka-config.yml.sample kafka-config.yml
# sudo systemctl restart newrelic-infra