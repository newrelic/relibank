# log parsing rule for the risk-assessment-service logs
###
# newrelic_log_parsing_rule.risk_assessment_parsing.id
###

resource "newrelic_log_parsing_rule" "risk_assessment_parsing" {
  name      = "risk_assessment_parsing"
  attribute = "message"
  enabled   = true
  grok = chomp(<<-EOT
    %%{LOGLEVEL:log_level} \[%%{DATA:timestamp:datetime:yyyy-MM-dd HH:mm:ss,SSS}\] risk_assessment_service: \{"message": %%{GREEDYDATA:jsondata:json({"noPrefix":true,"dropOriginal":true})}\}
    EOT
  )
  lucene = ""
  nrql   = "SELECT * FROM Log WHERE `container_name` = 'risk-assessment-service' AND message LIKE '%\"message\":%'"
}