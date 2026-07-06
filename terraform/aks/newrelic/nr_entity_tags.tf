# TMM: Replace this placeholder tag assignment with real team / owner / tier tags. Demogorgon's
# nr_entity_tags.tf iterates with `count` to tag every workload — pattern to extend.

resource "newrelic_entity_tags" "placeholder_workload_team" {
  guid = newrelic_workload.placeholder.guid

  tag {
    key    = "team"
    values = ["relibank"]
  }

  tag {
    key    = "environment"
    values = [var.demo_environment]
  }
}
