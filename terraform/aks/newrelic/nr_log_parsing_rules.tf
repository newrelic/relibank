# log parsing rules
###
# newrelic_log_parsing_rule.relibank_mobile_android_parsing.id
# newrelic_log_parsing_rule.risk_assessment_parsing.id
###

resource "newrelic_log_parsing_rule" "relibank_mobile_android_parsing" {
  name      = "relibank_mobile_android_parsing"
  attribute = "message"
  enabled   = true
  grok = chomp(<<-EOT
    "?\[CONSOLE\]\[%%{WORD:level}\]\{\"0\":\"%%{GREEDYDATA:jsondata:json({"noPrefix":true,"isEscaped":true,"dropOriginal":true})}\""?\}?
    EOT
  )
  lucene = ""
  nrql   = "SELECT * FROM Log WHERE collector.name = 'AndroidAgent' AND message LIKE '[CONSOLE]%'"
}

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