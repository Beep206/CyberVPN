TERRAFORM ?= terraform

.PHONY: terraform-fmt terraform-validate-staging-foundation terraform-init-staging-foundation \
	terraform-plan-staging-foundation terraform-validate-staging-edge terraform-init-staging-edge \
	terraform-plan-staging-edge terraform-validate-staging-dns terraform-init-staging-dns \
	terraform-plan-staging-dns terraform-validate-production-foundation terraform-init-production-foundation \
	terraform-plan-production-foundation terraform-validate-production-edge terraform-init-production-edge \
	terraform-plan-production-edge terraform-validate-production-dns terraform-init-production-dns \
	terraform-plan-production-dns terraform-init-staging-control-plane terraform-validate-staging-control-plane \
	terraform-plan-staging-control-plane terraform-init-production-control-plane \
	terraform-validate-production-control-plane terraform-plan-production-control-plane \
	inventory-staging inventory-production inventory-fixture-staging inventory-test \
	control-plane-release-staging control-plane-release-production \
	control-plane-vault-bootstrap-staging control-plane-vault-bootstrap-production \
	ansible-install ansible-syntax monitoring-validate \
	ansible-bootstrap-staging ansible-verify-staging ansible-remnawave-rollout-staging \
	ansible-remnawave-verify-staging ansible-remnawave-rollback-staging \
	remnawave-staging-smoke \
	ansible-helix-rollout-staging ansible-helix-verify-staging ansible-helix-rollback-staging \
	ansible-alloy-rollout-staging ansible-alloy-verify-staging ansible-alloy-rollback-staging \
	ansible-control-plane-rollout-staging ansible-control-plane-verify-staging \
	ansible-control-plane-rollback-staging ansible-control-plane-backup-staging \
	ansible-control-plane-restore-drill-staging \
	ansible-bootstrap-production ansible-verify-production ansible-remnawave-rollout-production \
	ansible-remnawave-verify-production ansible-remnawave-rollback-production \
	ansible-helix-rollout-production ansible-helix-verify-production ansible-helix-rollback-production \
	ansible-alloy-rollout-production ansible-alloy-verify-production ansible-alloy-rollback-production \
	ansible-control-plane-rollout-production ansible-control-plane-verify-production \
	ansible-control-plane-rollback-production ansible-control-plane-backup-production \
	ansible-control-plane-restore-drill-production \
	ansible-phase2-staging ansible-phase3-staging ansible-phase4-staging ansible-phase5-staging \
	ansible-phase6-remnawave-canary-production ansible-phase6-helix-canary-production \
	ansible-phase7-control-plane-staging

terraform-fmt:
	$(TERRAFORM) -chdir=terraform/live/staging/foundation fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/staging/edge fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/staging/dns fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/staging/control-plane fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/production/foundation fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/production/edge fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/production/dns fmt -recursive
	$(TERRAFORM) -chdir=terraform/live/production/control-plane fmt -recursive

terraform-init-staging-foundation:
	$(TERRAFORM) -chdir=terraform/live/staging/foundation init -backend-config=backend.hcl

terraform-validate-staging-foundation:
	$(TERRAFORM) -chdir=terraform/live/staging/foundation validate

terraform-plan-staging-foundation:
	$(TERRAFORM) -chdir=terraform/live/staging/foundation plan -var-file=terraform.tfvars

terraform-init-staging-edge:
	$(TERRAFORM) -chdir=terraform/live/staging/edge init -backend-config=backend.hcl

terraform-validate-staging-edge:
	$(TERRAFORM) -chdir=terraform/live/staging/edge validate

terraform-plan-staging-edge:
	$(TERRAFORM) -chdir=terraform/live/staging/edge plan -var-file=terraform.tfvars

terraform-init-staging-dns:
	$(TERRAFORM) -chdir=terraform/live/staging/dns init -backend-config=backend.hcl

terraform-validate-staging-dns:
	$(TERRAFORM) -chdir=terraform/live/staging/dns validate

terraform-plan-staging-dns:
	$(TERRAFORM) -chdir=terraform/live/staging/dns plan -var-file=terraform.tfvars

terraform-init-staging-control-plane:
	$(TERRAFORM) -chdir=terraform/live/staging/control-plane init -backend-config=backend.hcl

terraform-validate-staging-control-plane:
	$(TERRAFORM) -chdir=terraform/live/staging/control-plane validate

terraform-plan-staging-control-plane:
	$(TERRAFORM) -chdir=terraform/live/staging/control-plane plan -var-file=terraform.tfvars

terraform-init-production-foundation:
	$(TERRAFORM) -chdir=terraform/live/production/foundation init -backend-config=backend.hcl

terraform-validate-production-foundation:
	$(TERRAFORM) -chdir=terraform/live/production/foundation validate

terraform-plan-production-foundation:
	$(TERRAFORM) -chdir=terraform/live/production/foundation plan -var-file=terraform.tfvars

terraform-init-production-edge:
	$(TERRAFORM) -chdir=terraform/live/production/edge init -backend-config=backend.hcl

terraform-validate-production-edge:
	$(TERRAFORM) -chdir=terraform/live/production/edge validate

terraform-plan-production-edge:
	$(TERRAFORM) -chdir=terraform/live/production/edge plan -var-file=terraform.tfvars

terraform-init-production-dns:
	$(TERRAFORM) -chdir=terraform/live/production/dns init -backend-config=backend.hcl

terraform-validate-production-dns:
	$(TERRAFORM) -chdir=terraform/live/production/dns validate

terraform-plan-production-dns:
	$(TERRAFORM) -chdir=terraform/live/production/dns plan -var-file=terraform.tfvars

terraform-init-production-control-plane:
	$(TERRAFORM) -chdir=terraform/live/production/control-plane init -backend-config=backend.hcl

terraform-validate-production-control-plane:
	$(TERRAFORM) -chdir=terraform/live/production/control-plane validate

terraform-plan-production-control-plane:
	$(TERRAFORM) -chdir=terraform/live/production/control-plane plan -var-file=terraform.tfvars

inventory-staging:
	python ansible/scripts/generate_inventory.py \
		--terraform-bin $(TERRAFORM) \
		--terraform-dir terraform/live/staging/edge \
		--output ansible/inventories/staging/generated.hosts.json \
		--prometheus-output artifacts/prometheus/staging/alloy-edge.json \
		--environment staging

inventory-production:
	python ansible/scripts/generate_inventory.py \
		--terraform-bin $(TERRAFORM) \
		--terraform-dir terraform/live/production/edge \
		--output ansible/inventories/production/generated.hosts.json \
		--prometheus-output artifacts/prometheus/production/alloy-edge.json \
		--environment production

inventory-fixture-staging:
	python ansible/scripts/generate_inventory.py \
		--terraform-bin $(TERRAFORM) \
		--terraform-dir terraform/live/staging/edge \
		--terraform-output-file ansible/tests/fixtures/edge_nodes.sample.json \
		--output artifacts/iac-ci/generated.hosts.json \
		--prometheus-output artifacts/iac-ci/alloy-edge.json \
		--environment staging

inventory-test:
	python -m unittest discover -s ansible/tests -p 'test_*.py'

control-plane-release-staging:
	test -n "$(BACKEND_IMAGE)"
	test -n "$(WORKER_IMAGE)"
	test -n "$(HELIX_ADAPTER_IMAGE)"
	python ansible/scripts/promote_control_plane_release.py \
		--environment staging \
		--backend-image "$(BACKEND_IMAGE)" \
		--worker-image "$(WORKER_IMAGE)" \
		--helix-adapter-image "$(HELIX_ADAPTER_IMAGE)" \
		$(if $(SOURCE_COMMIT),--source-commit "$(SOURCE_COMMIT)",) \
		$(if $(SOURCE_RUN_URL),--source-run-url "$(SOURCE_RUN_URL)",) \
		$(if $(RELEASE_NAME),--release-name "$(RELEASE_NAME)",)

control-plane-release-production:
	test -n "$(BACKEND_IMAGE)"
	test -n "$(WORKER_IMAGE)"
	test -n "$(HELIX_ADAPTER_IMAGE)"
	python ansible/scripts/promote_control_plane_release.py \
		--environment production \
		--backend-image "$(BACKEND_IMAGE)" \
		--worker-image "$(WORKER_IMAGE)" \
		--helix-adapter-image "$(HELIX_ADAPTER_IMAGE)" \
		$(if $(SOURCE_COMMIT),--source-commit "$(SOURCE_COMMIT)",) \
		$(if $(SOURCE_RUN_URL),--source-run-url "$(SOURCE_RUN_URL)",) \
		$(if $(RELEASE_NAME),--release-name "$(RELEASE_NAME)",)

control-plane-vault-bootstrap-staging:
	test -n "$(SECRETS_SOURCE)"
	python ansible/scripts/bootstrap_control_plane_vault.py \
		--environment staging \
		--source "$(SECRETS_SOURCE)" \
		$(if $(ENCRYPT_VAULT),--encrypt,) \
		$(if $(VAULT_PASSWORD_FILE),--vault-password-file "$(VAULT_PASSWORD_FILE)",) \
		$(if $(VAULT_ID),--vault-id "$(VAULT_ID)",)

control-plane-vault-bootstrap-production:
	test -n "$(SECRETS_SOURCE)"
	python ansible/scripts/bootstrap_control_plane_vault.py \
		--environment production \
		--source "$(SECRETS_SOURCE)" \
		$(if $(ENCRYPT_VAULT),--encrypt,) \
		$(if $(VAULT_PASSWORD_FILE),--vault-password-file "$(VAULT_PASSWORD_FILE)",) \
		$(if $(VAULT_ID),--vault-id "$(VAULT_ID)",)

ansible-install:
	cd ansible && ansible-galaxy collection install -r requirements.yml

ansible-syntax:
	cd ansible && ansible-playbook -i inventories/staging playbooks/site.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/remnawave-rollout.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/remnawave-verify.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-remnawave.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/helix-rollout.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/helix-verify.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-helix.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/alloy-rollout.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/alloy-verify.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-alloy.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-rollout.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-verify.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-control-plane.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-backup.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-restore-drill.yml --syntax-check
	cd ansible && ansible-playbook -i inventories/production playbooks/remnawave-rollout.yml --syntax-check -e remnawave_edge_target_group=remnawave_edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/remnawave-verify.yml --syntax-check -e remnawave_edge_target_group=remnawave_edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-remnawave.yml --syntax-check -e remnawave_edge_target_group=remnawave_edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/helix-rollout.yml --syntax-check -e helix_edge_target_group=helix_edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/helix-verify.yml --syntax-check -e helix_edge_target_group=helix_edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-helix.yml --syntax-check -e helix_edge_target_group=helix_edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/alloy-rollout.yml --syntax-check -e edge_target_group=edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/alloy-verify.yml --syntax-check -e edge_target_group=edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-alloy.yml --syntax-check -e edge_target_group=edge_production
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-rollout.yml --syntax-check -e control_plane_target_group=control_plane_production
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-verify.yml --syntax-check -e control_plane_target_group=control_plane_production
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-control-plane.yml --syntax-check -e control_plane_target_group=control_plane_production
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-backup.yml --syntax-check -e control_plane_target_group=control_plane_production
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-restore-drill.yml --syntax-check -e control_plane_target_group=control_plane_production

monitoring-validate:
	bash tests/validate_dashboards.sh

ansible-bootstrap-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/edge-bootstrap.yml -e edge_target_group=edge_staging

ansible-verify-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/edge-verify.yml -e edge_target_group=edge_staging

ansible-phase2-staging: inventory-staging ansible-bootstrap-staging ansible-verify-staging

ansible-remnawave-rollout-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/remnawave-rollout.yml -e remnawave_edge_target_group=remnawave_edge_staging

ansible-remnawave-verify-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/remnawave-verify.yml -e remnawave_edge_target_group=remnawave_edge_staging

ansible-remnawave-rollback-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-remnawave.yml -e remnawave_edge_target_group=remnawave_edge_staging

remnawave-staging-smoke:
	./scripts/remnawave-staging-smoke.sh

ansible-phase3-staging: inventory-staging ansible-remnawave-rollout-staging ansible-remnawave-verify-staging

ansible-helix-rollout-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/helix-rollout.yml -e helix_edge_target_group=helix_edge_staging

ansible-helix-verify-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/helix-verify.yml -e helix_edge_target_group=helix_edge_staging

ansible-helix-rollback-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-helix.yml -e helix_edge_target_group=helix_edge_staging

ansible-phase4-staging: inventory-staging ansible-helix-rollout-staging ansible-helix-verify-staging

ansible-alloy-rollout-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/alloy-rollout.yml -e edge_target_group=edge_staging

ansible-alloy-verify-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/alloy-verify.yml -e edge_target_group=edge_staging

ansible-alloy-rollback-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-alloy.yml -e edge_target_group=edge_staging

ansible-phase5-staging: inventory-staging ansible-alloy-rollout-staging ansible-alloy-verify-staging

ansible-control-plane-rollout-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-rollout.yml -e control_plane_target_group=control_plane_staging

ansible-control-plane-verify-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-verify.yml -e control_plane_target_group=control_plane_staging

ansible-control-plane-rollback-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/rollback-control-plane.yml -e control_plane_target_group=control_plane_staging

ansible-control-plane-backup-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-backup.yml -e control_plane_target_group=control_plane_staging

ansible-control-plane-restore-drill-staging:
	cd ansible && ansible-playbook -i inventories/staging playbooks/control-plane-restore-drill.yml -e control_plane_target_group=control_plane_staging

ansible-phase7-control-plane-staging: ansible-control-plane-rollout-staging ansible-control-plane-verify-staging

ansible-bootstrap-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/edge-bootstrap.yml -e edge_target_group=edge_production

ansible-verify-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/edge-verify.yml -e edge_target_group=edge_production

ansible-remnawave-rollout-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/remnawave-rollout.yml -e remnawave_edge_target_group=remnawave_edge_production

ansible-remnawave-verify-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/remnawave-verify.yml -e remnawave_edge_target_group=remnawave_edge_production

ansible-remnawave-rollback-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-remnawave.yml -e remnawave_edge_target_group=remnawave_edge_production

ansible-helix-rollout-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/helix-rollout.yml -e helix_edge_target_group=helix_edge_production

ansible-helix-verify-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/helix-verify.yml -e helix_edge_target_group=helix_edge_production

ansible-helix-rollback-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-helix.yml -e helix_edge_target_group=helix_edge_production

ansible-alloy-rollout-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/alloy-rollout.yml -e edge_target_group=edge_production

ansible-alloy-verify-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/alloy-verify.yml -e edge_target_group=edge_production

ansible-alloy-rollback-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-alloy.yml -e edge_target_group=edge_production

ansible-control-plane-rollout-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-rollout.yml -e control_plane_target_group=control_plane_production

ansible-control-plane-verify-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-verify.yml -e control_plane_target_group=control_plane_production

ansible-control-plane-rollback-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/rollback-control-plane.yml -e control_plane_target_group=control_plane_production

ansible-control-plane-backup-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-backup.yml -e control_plane_target_group=control_plane_production

ansible-control-plane-restore-drill-production:
	cd ansible && ansible-playbook -i inventories/production playbooks/control-plane-restore-drill.yml -e control_plane_target_group=control_plane_production

ansible-phase6-remnawave-canary-production: inventory-production
	test -n "$(PROD_REMNAWAVE_CANARY_HOST)"
	cd ansible && ansible-playbook -i inventories/production playbooks/remnawave-rollout.yml \
		-e remnawave_edge_target_group=remnawave_edge_production \
		--limit "$(PROD_REMNAWAVE_CANARY_HOST)"
	cd ansible && ansible-playbook -i inventories/production playbooks/remnawave-verify.yml \
		-e remnawave_edge_target_group=remnawave_edge_production \
		--limit "$(PROD_REMNAWAVE_CANARY_HOST)"
	cd ansible && ansible-playbook -i inventories/production playbooks/alloy-verify.yml \
		-e edge_target_group=edge_production \
		--limit "$(PROD_REMNAWAVE_CANARY_HOST)"

ansible-phase6-helix-canary-production: inventory-production
	test -n "$(PROD_HELIX_CANARY_HOST)"
	cd ansible && ansible-playbook -i inventories/production playbooks/helix-rollout.yml \
		-e helix_edge_target_group=helix_edge_production \
		--limit "$(PROD_HELIX_CANARY_HOST)"
	cd ansible && ansible-playbook -i inventories/production playbooks/helix-verify.yml \
		-e helix_edge_target_group=helix_edge_production \
		--limit "$(PROD_HELIX_CANARY_HOST)"
	cd ansible && ansible-playbook -i inventories/production playbooks/alloy-verify.yml \
		-e edge_target_group=edge_production \
		--limit "$(PROD_HELIX_CANARY_HOST)"
