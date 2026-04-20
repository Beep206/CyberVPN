# CyberVPN Partner Portal Metric Catalog

**Date:** 2026-04-20  
**Status:** Metric catalog  
**Purpose:** provide the baseline catalog of required partner-platform metrics, their bounded labels, sources, dashboards, and alert relationships.

---

## 1. Document Role

This document is the metric inventory for the partner platform.

Each metric row defines:

- metric name;
- type;
- unit;
- bounded label policy;
- source;
- target dashboard;
- alert or operational use;
- owning team.

This catalog is the default contract for implementation unless a later change is explicitly approved.

---

## 2. Shared Label Conventions

Shorthand used in the tables below:

- `core_http` = `env,service,surface,realm_type,principal_class,endpoint_template,method,status_class,error_code,result`
- `workflow` = `env,service,surface,workspace_status,lane,result,reason_code`
- `finance` = `env,service,surface,lane,settlement_state,payout_state,payout_rail,currency,result,reason_code`
- `ops` = `env,service,surface,notification_type,case_type,integration_type,job_name,queue_name,result`
- `admin_ops` = `env,service,surface,admin_action_type,object_type,role,result,maker_checker_state`

All labels remain subject to the master label policy in the observability spec.

---

## 3. Backend API Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `http_server_request_duration_seconds` | histogram | seconds | `core_http` | backend | API Health | latency SLI | backend |
| `http_server_requests_total` | counter | total | `core_http` | backend | API Health | traffic/error rate | backend |
| `http_client_request_duration_seconds` | histogram | seconds | `env,service,target_service,method,status_class,result` | backend | API Health | downstream latency | backend |
| `http_client_requests_total` | counter | total | `env,service,target_service,method,status_class,result,error_code` | backend | API Health | dependency error rate | backend |
| `cybervpn_partner_api_errors_total` | counter | total | `core_http` | backend | API Health | API failure spikes | backend |
| `cybervpn_partner_api_permission_denied_total` | counter | total | `env,service,surface,principal_class,endpoint_template,permission_key,reason_code` | backend | API Health | authz drift | backend |
| `cybervpn_partner_api_workspace_scope_denied_total` | counter | total | `env,service,surface,endpoint_template,reason_code` | backend | API Health | tenant-scope violations | backend |
| `cybervpn_partner_api_realm_mismatch_total` | counter | total | `env,service,surface,realm_type,principal_class,reason_code` | backend | API Health | security anomaly | backend |
| `cybervpn_partner_api_idempotency_replays_total` | counter | total | `env,service,surface,endpoint_template,result` | backend | API Health | duplicate request analysis | backend |
| `cybervpn_partner_api_idempotency_conflicts_total` | counter | total | `env,service,surface,endpoint_template,reason_code` | backend | API Health | mutation conflict alerting | backend |

---

## 4. Frontend UX Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_frontend_route_load_duration_seconds` | histogram | seconds | `env,surface,route_group,workspace_status,lane,result` | partner frontend | Frontend UX | route latency | frontend |
| `cybervpn_partner_frontend_api_call_duration_seconds` | histogram | seconds | `env,surface,route_group,endpoint_template,result,error_code` | partner frontend | Frontend UX | browser API latency | frontend |
| `cybervpn_partner_frontend_unhandled_errors_total` | counter | total | `env,surface,route_group,error_code` | partner frontend | Frontend UX | JS error spikes | frontend |
| `cybervpn_partner_frontend_render_errors_total` | counter | total | `env,surface,route_group,error_code` | partner frontend | Frontend UX | render regressions | frontend |
| `cybervpn_partner_frontend_route_guard_blocks_total` | counter | total | `env,surface,route_group,workspace_status,lane,blocked_reason` | partner frontend | Frontend UX | UX/authz insight | frontend |
| `cybervpn_partner_frontend_form_validation_errors_total` | counter | total | `env,surface,route_group,form_name,error_code` | partner frontend | Frontend UX | onboarding friction | frontend |
| `cybervpn_partner_frontend_submit_attempts_total` | counter | total | `env,surface,route_group,form_name,result` | partner frontend | Frontend UX | submit conversion | frontend |
| `cybervpn_partner_frontend_submit_failures_total` | counter | total | `env,surface,route_group,form_name,error_code` | partner frontend | Frontend UX | submit regressions | frontend |
| `cybervpn_partner_frontend_lcp_seconds` | histogram | seconds | `env,surface,route_group,release_ring` | partner frontend | Frontend UX | Web Vitals | frontend |
| `cybervpn_partner_frontend_inp_seconds` | histogram | seconds | `env,surface,route_group,release_ring` | partner frontend | Frontend UX | Web Vitals | frontend |
| `cybervpn_partner_frontend_cls_ratio` | histogram | ratio | `env,surface,route_group,release_ring` | partner frontend | Frontend UX | Web Vitals | frontend |
| `cybervpn_partner_frontend_ttfb_seconds` | histogram | seconds | `env,surface,route_group,release_ring` | partner frontend | Frontend UX | Web Vitals | frontend |

---

## 5. Auth, Realm, Session, And Bootstrap Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_auth_login_attempts_total` | counter | total | `env,service,surface,realm_type,principal_class,result,reason` | backend | API Health | auth volume | backend |
| `cybervpn_partner_auth_login_success_total` | counter | total | `env,service,surface,realm_type,principal_class` | backend | API Health | auth SLI | backend |
| `cybervpn_partner_auth_login_failures_total` | counter | total | `env,service,surface,realm_type,principal_class,reason` | backend | API Health | login failure spike | backend |
| `cybervpn_partner_auth_refresh_attempts_total` | counter | total | `env,service,surface,realm_type,principal_class,result,reason` | backend | API Health | refresh path health | backend |
| `cybervpn_partner_auth_refresh_failures_total` | counter | total | `env,service,surface,realm_type,principal_class,reason` | backend | API Health | refresh failures | backend |
| `cybervpn_partner_auth_logout_total` | counter | total | `env,service,surface,realm_type,principal_class` | backend | API Health | session lifecycle | backend |
| `cybervpn_partner_auth_password_reset_requested_total` | counter | total | `env,service,surface,realm_type,result` | backend | API Health | reset flow health | backend |
| `cybervpn_partner_auth_email_verification_total` | counter | total | `env,service,surface,realm_type,result` | backend | API Health | onboarding checkpoint | backend |
| `cybervpn_partner_auth_mfa_challenges_total` | counter | total | `env,service,surface,realm_type,result` | backend | API Health | MFA flow health | backend |
| `cybervpn_partner_auth_mfa_failures_total` | counter | total | `env,service,surface,realm_type,reason` | backend | API Health | MFA anomalies | backend |
| `cybervpn_partner_auth_wrong_host_token_rejected_total` | counter | total | `env,service,surface,realm_type,reason` | backend | API Health | wrong-host security alert | backend |
| `cybervpn_partner_auth_cross_realm_denied_total` | counter | total | `env,service,surface,realm_type,principal_class,reason` | backend | API Health | realm leakage detection | backend |
| `cybervpn_partner_auth_csrf_rejections_total` | counter | total | `env,service,surface,endpoint_template` | backend | API Health | browser security regression | backend |
| `cybervpn_partner_auth_cors_rejections_total` | counter | total | `env,service,surface,endpoint_template` | backend | API Health | origin policy regression | backend |
| `cybervpn_partner_bootstrap_requests_total` | counter | total | `env,service,surface,workspace_status,principal_class,result` | backend | API Health | bootstrap traffic | backend |
| `cybervpn_partner_bootstrap_duration_seconds` | histogram | seconds | `env,service,surface,workspace_status,principal_class,result` | backend | API Health | bootstrap latency SLI | backend |
| `cybervpn_partner_bootstrap_failures_total` | counter | total | `env,service,surface,workspace_status,error_code` | backend | API Health | bootstrap failures | backend |
| `cybervpn_partner_route_guard_blocks_total` | counter | total | `env,surface,route_group,workspace_status,lane,blocked_reason` | partner frontend | Frontend UX | access restriction patterns | frontend |
| `cybervpn_partner_route_visibility_evaluations_total` | counter | total | `env,surface,route_group,workspace_status,lane,result` | partner frontend | Frontend UX | visibility logic health | frontend |

---

## 6. Application And Onboarding Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_application_drafts_created_total` | counter | total | `workflow,review_level` | backend | Onboarding Funnel | funnel top | product/backend |
| `cybervpn_partner_application_drafts_saved_total` | counter | total | `workflow,result` | backend | Onboarding Funnel | autosave health | product/backend |
| `cybervpn_partner_application_submissions_total` | counter | total | `workflow,review_level` | backend | Onboarding Funnel | submit conversion | product/backend |
| `cybervpn_partner_application_submit_duration_seconds` | histogram | seconds | `workflow,result` | backend | Onboarding Funnel | submit latency | backend |
| `cybervpn_partner_applications_pending` | gauge | total | `env,service,lane,review_level` | backend | Review Ops | queue size | partner ops |
| `cybervpn_partner_applications_under_review` | gauge | total | `env,service,lane,review_level` | backend | Review Ops | review inventory | partner ops |
| `cybervpn_partner_applications_needs_info` | gauge | total | `env,service,lane,review_level` | backend | Review Ops | rework backlog | partner ops |
| `cybervpn_partner_application_decisions_total` | counter | total | `workflow,decision,review_level` | backend | Review Ops | decision mix | partner ops |
| `cybervpn_partner_application_decision_duration_seconds` | histogram | seconds | `env,service,lane,decision,review_level` | backend | Review Ops | time to decision | partner ops |
| `cybervpn_partner_application_requested_info_total` | counter | total | `workflow,review_level,reason_code` | backend | Review Ops | needs-info rate | partner ops |
| `cybervpn_partner_application_evidence_uploads_total` | counter | total | `workflow,result` | backend | Onboarding Funnel | evidence usage | backend |
| `cybervpn_partner_application_evidence_upload_failures_total` | counter | total | `workflow,error_code` | backend | Onboarding Funnel | upload regression | backend |

---

## 7. Workspace, Team, RBAC, And Program Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_workspace_created_total` | counter | total | `env,service,surface,workspace_status,lane,result` | backend | Executive Overview | workspace growth | product/backend |
| `cybervpn_partner_workspace_status_transitions_total` | counter | total | `env,service,from_status,to_status,lane,result` | backend | Executive Overview | lifecycle flow | product/backend |
| `cybervpn_partner_workspace_members_total` | gauge | total | `env,service,workspace_status,role` | backend | Admin Partner Ops | team size posture | backend |
| `cybervpn_partner_team_invitations_sent_total` | counter | total | `env,service,workspace_status,role,result` | backend | Admin Partner Ops | invite health | backend |
| `cybervpn_partner_team_invitations_accepted_total` | counter | total | `env,service,workspace_status,role` | backend | Admin Partner Ops | invite conversion | backend |
| `cybervpn_partner_team_invitations_expired_total` | counter | total | `env,service,workspace_status,role` | backend | Admin Partner Ops | onboarding friction | backend |
| `cybervpn_partner_permission_denials_total` | counter | total | `env,service,surface,permission_key,role,reason_code` | backend | API Health | authz regression | backend |
| `cybervpn_partner_role_changes_total` | counter | total | `env,service,role,result` | backend | Admin Partner Ops | sensitive changes | backend |
| `cybervpn_partner_mfa_enabled_total` | counter | total | `env,service,surface,role,result` | backend | API Health | security posture | backend |
| `cybervpn_partner_lane_applications_total` | counter | total | `env,service,lane,result,reason_code` | backend | Executive Overview | lane demand | product/backend |
| `cybervpn_partner_lane_memberships_active` | gauge | total | `env,service,lane,workspace_status` | backend | Executive Overview | live lane inventory | product/backend |
| `cybervpn_partner_lane_membership_transitions_total` | counter | total | `env,service,lane,from_status,to_status,result` | backend | Executive Overview | lane flow | product/backend |
| `cybervpn_partner_lane_restrictions_active` | gauge | total | `env,service,lane,restriction_type` | backend | Risk / Compliance | live restrictions | risk |
| `cybervpn_partner_lane_probation_promotions_total` | counter | total | `env,service,lane,result` | backend | Executive Overview | probation completion | partner ops |

---

## 8. Codes, Tracking, Attribution, Orders, And Growth Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_codes_created_total` | counter | total | `env,service,lane,program_type,code_type,result` | backend | Codes / Tracking | code volume | growth/backend |
| `cybervpn_partner_codes_activated_total` | counter | total | `env,service,lane,program_type,code_type,result` | backend | Codes / Tracking | activation flow | growth/backend |
| `cybervpn_partner_codes_paused_total` | counter | total | `env,service,lane,code_type,reason_code` | backend | Codes / Tracking | governance or ops signal | growth/backend |
| `cybervpn_partner_codes_revoked_total` | counter | total | `env,service,lane,code_type,reason_code` | backend | Codes / Tracking | revocation events | growth/backend |
| `cybervpn_partner_tracking_links_created_total` | counter | total | `env,service,lane,program_type,result` | backend | Codes / Tracking | tracking usage | growth/backend |
| `cybervpn_partner_qr_codes_generated_total` | counter | total | `env,service,lane,program_type,result` | backend | Codes / Tracking | QR usage | growth/backend |
| `cybervpn_partner_tracking_clicks_total` | counter | total | `env,service,lane,program_type,code_type,result` | backend | Codes / Tracking | click volume | growth/backend |
| `cybervpn_partner_tracking_clicks_rejected_total` | counter | total | `env,service,lane,program_type,reject_reason` | backend | Codes / Tracking | invalid click rate | growth/backend |
| `cybervpn_partner_touchpoints_recorded_total` | counter | total | `env,service,touchpoint_type,owner_type,owner_source,lane,result` | backend | Attribution | touchpoint volume | growth/backend |
| `cybervpn_partner_touchpoints_rejected_total` | counter | total | `env,service,touchpoint_type,lane,reason_code` | backend | Attribution | touchpoint rejection rate | growth/backend |
| `cybervpn_partner_attribution_resolutions_total` | counter | total | `env,service,owner_type,owner_source,lane,result,reason_code` | backend | Attribution | attribution health | growth/backend |
| `cybervpn_partner_attribution_resolution_duration_seconds` | histogram | seconds | `env,service,owner_type,lane,result` | backend | Attribution | resolution latency | growth/backend |
| `cybervpn_partner_attribution_no_owner_total` | counter | total | `env,service,touchpoint_type,lane,reason_code` | backend | Attribution | no-owner alerting | growth/backend |
| `cybervpn_partner_attribution_conflicts_total` | counter | total | `env,service,lane,reason_code` | backend | Attribution | conflict spikes | growth/backend |
| `cybervpn_partner_attribution_manual_overrides_total` | counter | total | `env,service,owner_type,lane,reason_code` | backend | Attribution | unexpected override usage | growth/backend |
| `cybervpn_partner_customer_bindings_created_total` | counter | total | `env,service,owner_type,lane,result` | backend | Attribution | binding creation | growth/backend |
| `cybervpn_partner_customer_bindings_blocked_total` | counter | total | `env,service,owner_type,lane,reason_code` | backend | Attribution | binding anomalies | growth/backend |
| `cybervpn_partner_orders_created_total` | counter | total | `env,service,lane,program_type,owner_type,payment_provider,result` | backend | Attribution | order volume | commerce/backend |
| `cybervpn_partner_orders_paid_total` | counter | total | `env,service,lane,program_type,owner_type,payment_provider,result` | backend | Executive Overview | paid conversion flow | commerce/backend |
| `cybervpn_partner_orders_refunded_total` | counter | total | `env,service,lane,payment_provider,result` | backend | Finance / Payouts | refund input | finance |
| `cybervpn_partner_orders_disputed_total` | counter | total | `env,service,lane,payment_provider,result` | backend | Finance / Payouts | dispute input | finance |
| `cybervpn_partner_qualifying_first_payments_total` | counter | total | `env,service,lane,program_type,owner_type,result` | backend | Executive Overview | first-paid KPI | commerce/backend |
| `cybervpn_partner_commissionability_evaluations_total` | counter | total | `env,service,lane,program_type,result,reject_reason` | backend | Attribution | commissionability flow | commerce/backend |
| `cybervpn_partner_commissionability_rejections_total` | counter | total | `env,service,lane,program_type,reject_reason` | backend | Attribution | rejection analysis | commerce/backend |
| `cybervpn_partner_commissionable_net_amount_usd_total` | counter | usd | `env,service,lane,program_type,owner_type,result` | backend | Executive Overview | monetized output | finance/backend |
| `cybervpn_partner_growth_rewards_allocated_total` | counter | total | `env,service,reward_type,surface,result,reason_code` | backend | Executive Overview | growth reward flow | growth/backend |
| `cybervpn_partner_growth_rewards_reversed_total` | counter | total | `env,service,reward_type,surface,reason_code` | backend | Executive Overview | reversal anomalies | growth/backend |
| `cybervpn_partner_referral_credits_allocated_usd_total` | counter | usd | `env,service,reward_type,surface,result` | backend | Executive Overview | growth accounting | growth/backend |
| `cybervpn_partner_invite_rewards_allocated_total` | counter | total | `env,service,reward_type,surface,result` | backend | Executive Overview | invite reward flow | growth/backend |
| `cybervpn_partner_growth_reward_failures_total` | counter | total | `env,service,reward_type,surface,error_code` | backend | Executive Overview | allocation failures | growth/backend |

---

## 9. Finance, Settlement, Refund, And Dispute Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_earnings_created_total` | counter | total | `finance` | backend | Finance / Payouts | earning flow | finance/backend |
| `cybervpn_partner_earnings_created_usd_total` | counter | usd | `finance` | backend | Finance / Payouts | gross earnings | finance/backend |
| `cybervpn_partner_earnings_on_hold_usd` | gauge | usd | `env,service,lane,settlement_state,currency` | backend | Finance / Payouts | held earnings | finance/backend |
| `cybervpn_partner_earnings_available_usd` | gauge | usd | `env,service,lane,settlement_state,currency` | backend | Finance / Payouts | available balance | finance/backend |
| `cybervpn_partner_earnings_reserved_usd` | gauge | usd | `env,service,lane,settlement_state,currency` | backend | Finance / Payouts | reserve balance | finance/backend |
| `cybervpn_partner_earnings_clawed_back_usd_total` | counter | usd | `finance` | backend | Finance / Payouts | clawback trend | finance/backend |
| `cybervpn_partner_holds_created_total` | counter | total | `finance` | backend | Finance / Payouts | hold creation | finance/backend |
| `cybervpn_partner_holds_released_total` | counter | total | `finance` | backend | Finance / Payouts | hold release flow | finance/backend |
| `cybervpn_partner_holds_extended_total` | counter | total | `finance` | backend | Finance / Payouts | extended hold signal | finance/backend |
| `cybervpn_partner_hold_release_duration_seconds` | histogram | seconds | `finance` | backend | Finance / Payouts | hold aging | finance/backend |
| `cybervpn_partner_statements_open` | gauge | total | `env,service,lane,settlement_state,currency` | backend | Finance / Payouts | statement inventory | finance/backend |
| `cybervpn_partner_statements_closed_total` | counter | total | `finance` | backend | Finance / Payouts | closing throughput | finance/backend |
| `cybervpn_partner_statement_close_duration_seconds` | histogram | seconds | `finance` | backend | Finance / Payouts | close latency | finance/backend |
| `cybervpn_partner_statement_reopen_total` | counter | total | `finance` | backend | Finance / Payouts | reopen anomaly | finance/backend |
| `cybervpn_partner_statement_adjustments_total` | counter | total | `finance` | backend | Finance / Payouts | adjustment flow | finance/backend |
| `cybervpn_partner_payout_accounts_created_total` | counter | total | `finance` | backend | Finance / Payouts | onboarding throughput | finance/backend |
| `cybervpn_partner_payout_accounts_verified_total` | counter | total | `finance` | backend | Finance / Payouts | verification throughput | finance/backend |
| `cybervpn_partner_payout_accounts_rejected_total` | counter | total | `finance` | backend | Finance / Payouts | onboarding rejection | finance/backend |
| `cybervpn_partner_payout_instructions_created_total` | counter | total | `finance,maker_checker_state` | backend | Finance / Payouts | payout instruction flow | finance/backend |
| `cybervpn_partner_payout_executions_total` | counter | total | `finance,maker_checker_state` | backend | Finance / Payouts | payout throughput | finance/backend |
| `cybervpn_partner_payout_execution_duration_seconds` | histogram | seconds | `finance,maker_checker_state` | backend | Finance / Payouts | payout latency | finance/backend |
| `cybervpn_partner_payout_failures_total` | counter | total | `finance,maker_checker_state` | backend | Finance / Payouts | payout failure alerts | finance/backend |
| `cybervpn_partner_payout_liability_usd` | gauge | usd | `env,service,lane,payout_state,currency` | backend | Finance / Payouts | liability monitoring | finance/backend |
| `cybervpn_partner_reconciliation_mismatches_total` | counter | total | `finance,reason_code` | backend | Finance / Payouts | critical integrity alert | finance/backend |
| `cybervpn_partner_refunds_created_total` | counter | total | `env,service,lane,payment_provider,result` | backend | Finance / Payouts | refund volume | finance/backend |
| `cybervpn_partner_refund_amount_usd_total` | counter | usd | `env,service,lane,payment_provider,result` | backend | Finance / Payouts | refund exposure | finance/backend |
| `cybervpn_partner_payment_disputes_created_total` | counter | total | `env,service,lane,payment_provider,dispute_stage,result` | backend | Finance / Payouts | dispute volume | finance/backend |
| `cybervpn_partner_payment_dispute_amount_usd_total` | counter | usd | `env,service,lane,payment_provider,dispute_stage,result` | backend | Finance / Payouts | dispute exposure | finance/backend |
| `cybervpn_partner_payment_dispute_outcomes_total` | counter | total | `env,service,lane,payment_provider,dispute_stage,dispute_outcome` | backend | Finance / Payouts | dispute win/loss | finance/backend |

Derived, not raw by default:

- refund rate;
- chargeback rate;
- dispute loss rate.

---

## 10. Compliance, Risk, Governance, Notifications, Cases, And Integrations

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_partner_risk_reviews_created_total` | counter | total | `env,service,lane,review_type,severity,result` | backend | Risk / Compliance | risk volume | risk |
| `cybervpn_partner_risk_reviews_open` | gauge | total | `env,service,lane,review_type,severity` | backend | Risk / Compliance | backlog | risk |
| `cybervpn_partner_risk_review_duration_seconds` | histogram | seconds | `env,service,lane,review_type,severity,result` | backend | Risk / Compliance | SLA | risk |
| `cybervpn_partner_risk_review_sla_breaches_total` | counter | total | `env,service,lane,review_type,severity` | backend | Risk / Compliance | SLA alerting | risk |
| `cybervpn_partner_traffic_declarations_submitted_total` | counter | total | `env,service,lane,declaration_type,result` | backend | Risk / Compliance | declaration demand | compliance |
| `cybervpn_partner_traffic_declarations_approved_total` | counter | total | `env,service,lane,declaration_type,result` | backend | Risk / Compliance | approval throughput | compliance |
| `cybervpn_partner_traffic_declarations_rejected_total` | counter | total | `env,service,lane,declaration_type,reason_code` | backend | Risk / Compliance | rejection trend | compliance |
| `cybervpn_partner_creative_approvals_submitted_total` | counter | total | `env,service,lane,creative_type,result` | backend | Risk / Compliance | creative queue | compliance |
| `cybervpn_partner_creative_approvals_approved_total` | counter | total | `env,service,lane,creative_type,result` | backend | Risk / Compliance | approval throughput | compliance |
| `cybervpn_partner_creative_approvals_rejected_total` | counter | total | `env,service,lane,creative_type,reason_code` | backend | Risk / Compliance | rejection trend | compliance |
| `cybervpn_partner_governance_actions_total` | counter | total | `env,service,lane,governance_action_type,severity,result` | backend | Risk / Compliance | governance spikes | risk |
| `cybervpn_partner_policy_acceptances_total` | counter | total | `env,service,surface,lane,result` | backend | Risk / Compliance | policy adoption | compliance |
| `cybervpn_partner_legal_acceptance_required_total` | counter | total | `env,service,surface,lane,result` | backend | Risk / Compliance | legal backlog | compliance |
| `cybervpn_partner_notifications_generated_total` | counter | total | `env,service,surface,notification_type,recipient_scope,result` | backend | Notifications / Cases | event volume | platform/backend |
| `cybervpn_partner_notifications_delivery_failures_total` | counter | total | `env,service,surface,notification_type,recipient_scope,error_code` | backend | Notifications / Cases | delivery failure alerting | platform/backend |
| `cybervpn_partner_notifications_unread` | gauge | total | `env,service,surface,notification_type,recipient_scope` | backend | Notifications / Cases | unread backlog | platform/backend |
| `cybervpn_partner_notification_action_required` | gauge | total | `env,service,surface,notification_type,recipient_scope` | backend | Notifications / Cases | action backlog | platform/backend |
| `cybervpn_partner_notification_delivery_duration_seconds` | histogram | seconds | `env,service,surface,notification_type,recipient_scope,result` | backend | Notifications / Cases | async delivery latency | platform/backend |
| `cybervpn_partner_cases_created_total` | counter | total | `env,service,surface,case_type,case_priority,result` | backend | Notifications / Cases | case inflow | support |
| `cybervpn_partner_cases_open` | gauge | total | `env,service,surface,case_type,case_priority` | backend | Notifications / Cases | open backlog | support |
| `cybervpn_partner_cases_resolved_total` | counter | total | `env,service,surface,case_type,case_priority,result` | backend | Notifications / Cases | resolution flow | support |
| `cybervpn_partner_case_first_response_duration_seconds` | histogram | seconds | `env,service,surface,case_type,case_priority,result` | backend | Notifications / Cases | SLA | support |
| `cybervpn_partner_case_resolution_duration_seconds` | histogram | seconds | `env,service,surface,case_type,case_priority,result` | backend | Notifications / Cases | SLA | support |
| `cybervpn_partner_case_sla_breaches_total` | counter | total | `env,service,surface,case_type,case_priority` | backend | Notifications / Cases | SLA breach alerting | support |
| `cybervpn_partner_api_tokens_created_total` | counter | total | `env,service,surface,integration_type,result` | backend | Integrations / Postbacks / Exports | token issuance | platform/backend |
| `cybervpn_partner_api_token_auth_failures_total` | counter | total | `env,service,surface,integration_type,reason_code` | backend | Integrations / Postbacks / Exports | auth misuse | platform/backend |
| `cybervpn_partner_postbacks_sent_total` | counter | total | `env,service,surface,integration_type,event_type,delivery_result` | worker/backend | Integrations / Postbacks / Exports | delivery volume | platform/backend |
| `cybervpn_partner_postbacks_success_total` | counter | total | `env,service,surface,integration_type,event_type` | worker/backend | Integrations / Postbacks / Exports | success rate numerator | platform/backend |
| `cybervpn_partner_postbacks_failed_total` | counter | total | `env,service,surface,integration_type,event_type,failure_reason` | worker/backend | Integrations / Postbacks / Exports | failure alerting | platform/backend |
| `cybervpn_partner_postback_delivery_duration_seconds` | histogram | seconds | `env,service,surface,integration_type,event_type,delivery_result` | worker/backend | Integrations / Postbacks / Exports | delivery latency | platform/backend |
| `cybervpn_partner_postback_retries_total` | counter | total | `env,service,surface,integration_type,event_type,failure_reason` | worker/backend | Integrations / Postbacks / Exports | retry growth | platform/backend |
| `cybervpn_partner_postback_dead_letter_total` | counter | total | `env,service,surface,integration_type,event_type,failure_reason` | worker/backend | Integrations / Postbacks / Exports | dead-letter alert | platform/backend |
| `cybervpn_partner_exports_requested_total` | counter | total | `env,service,surface,integration_type,result` | backend/worker | Integrations / Postbacks / Exports | export demand | platform/backend |
| `cybervpn_partner_exports_completed_total` | counter | total | `env,service,surface,integration_type,result` | backend/worker | Integrations / Postbacks / Exports | export completion | platform/backend |
| `cybervpn_partner_exports_failed_total` | counter | total | `env,service,surface,integration_type,failure_reason` | backend/worker | Integrations / Postbacks / Exports | export failure spikes | platform/backend |
| `cybervpn_partner_export_duration_seconds` | histogram | seconds | `env,service,surface,integration_type,result` | backend/worker | Integrations / Postbacks / Exports | export latency | platform/backend |

---

## 11. Admin Operations, Workers, Event Pipeline, And Infrastructure Metrics

| Metric | Type | Unit | Labels | Source | Dashboard | Alert / Use | Owner |
|---|---|---|---|---|---|---|---|
| `cybervpn_admin_partner_actions_total` | counter | total | `admin_ops` | backend/admin | Admin Partner Ops | operator activity | admin/backend |
| `cybervpn_admin_partner_review_queue_open` | gauge | total | `env,service,object_type,role` | backend/admin | Admin Partner Ops | queue backlog | partner ops |
| `cybervpn_admin_partner_review_duration_seconds` | histogram | seconds | `admin_ops` | backend/admin | Admin Partner Ops | review SLA | partner ops |
| `cybervpn_admin_partner_privileged_reads_total` | counter | total | `admin_ops` | backend/admin | Admin Partner Ops | unusual read spikes | admin/backend |
| `cybervpn_admin_partner_maker_checker_actions_total` | counter | total | `admin_ops` | backend/admin | Admin Partner Ops | maker-checker flow | finance ops |
| `cybervpn_admin_partner_audit_events_total` | counter | total | `admin_ops` | backend/admin | Admin Partner Ops | audit write health | admin/backend |
| `cybervpn_partner_worker_jobs_started_total` | counter | total | `env,service,job_name,queue_name,result` | worker | Observability Pipeline | job volume | backend/platform |
| `cybervpn_partner_worker_jobs_completed_total` | counter | total | `env,service,job_name,queue_name,result` | worker | Observability Pipeline | completion rate | backend/platform |
| `cybervpn_partner_worker_jobs_failed_total` | counter | total | `env,service,job_name,queue_name,failure_reason` | worker | Observability Pipeline | worker failure spike | backend/platform |
| `cybervpn_partner_worker_job_duration_seconds` | histogram | seconds | `env,service,job_name,queue_name,result` | worker | Observability Pipeline | job latency | backend/platform |
| `cybervpn_partner_worker_queue_depth` | gauge | total | `env,service,queue_name` | worker | Observability Pipeline | queue backlog | backend/platform |
| `cybervpn_partner_worker_queue_oldest_age_seconds` | gauge | seconds | `env,service,queue_name` | worker | Observability Pipeline | queue aging alert | backend/platform |
| `cybervpn_partner_worker_dead_letter_total` | counter | total | `env,service,job_name,queue_name,failure_reason` | worker | Observability Pipeline | dead-letter alert | backend/platform |
| `cybervpn_partner_outbox_events_created_total` | counter | total | `env,service,event_type,result` | backend | Observability Pipeline | outbox flow | backend/platform |
| `cybervpn_partner_outbox_events_published_total` | counter | total | `env,service,event_type,result` | backend/worker | Observability Pipeline | outbox publish success | backend/platform |
| `cybervpn_partner_outbox_publish_failures_total` | counter | total | `env,service,event_type,failure_reason` | backend/worker | Observability Pipeline | publish failure alert | backend/platform |
| `cybervpn_partner_outbox_lag_seconds` | gauge | seconds | `env,service,event_type` | backend/worker | Observability Pipeline | lag | backend/platform |
| `cybervpn_partner_outbox_unpublished` | gauge | total | `env,service,event_type` | backend/worker | Observability Pipeline | backlog | backend/platform |
| `cybervpn_partner_event_consumer_lag_seconds` | gauge | seconds | `env,service,consumer_name,event_type` | worker | Observability Pipeline | consumer lag | backend/platform |
| `cybervpn_partner_event_consumer_failures_total` | counter | total | `env,service,consumer_name,event_type,failure_reason` | worker | Observability Pipeline | consumer failure alert | backend/platform |
| `cybervpn_partner_event_schema_mismatches_total` | counter | total | `env,service,consumer_name,event_type` | backend/worker | Observability Pipeline | schema mismatch alert | backend/platform |
| `otelcol_receiver_accepted_spans` | counter | spans | exporter-native | otel collector | Observability Pipeline | ingest health | SRE |
| `otelcol_receiver_refused_spans` | counter | spans | exporter-native | otel collector | Observability Pipeline | telemetry loss alert | SRE |
| `otelcol_exporter_sent_spans` | counter | spans | exporter-native | otel collector | Observability Pipeline | export health | SRE |
| `otelcol_exporter_send_failed_spans` | counter | spans | exporter-native | otel collector | Observability Pipeline | export failure alert | SRE |
| `otelcol_processor_dropped_spans` | counter | spans | exporter-native | otel collector | Observability Pipeline | dropped traces | SRE |
| `prometheus_target_interval_length_seconds` | histogram | seconds | exporter-native | Prometheus | Observability Pipeline | scrape jitter | SRE |
| `prometheus_target_scrape_pool_targets` | gauge | total | exporter-native | Prometheus | Observability Pipeline | target inventory | SRE |
| `loki_distributor_bytes_received_total` | counter | bytes | exporter-native | Loki | Observability Pipeline | log ingest | SRE |
| `promtail_read_bytes_total` | counter | bytes | exporter-native | Promtail | Observability Pipeline | scrape activity | SRE |
| `tempo_distributor_spans_received_total` | counter | total | exporter-native | Tempo | Observability Pipeline | trace ingest | SRE |
| `process_cpu_seconds_total` | counter | seconds | exporter-native | services/exporters | Infrastructure | CPU | SRE |
| `process_resident_memory_bytes` | gauge | bytes | exporter-native | services/exporters | Infrastructure | memory | SRE |
| `container_cpu_usage_seconds_total` | counter | seconds | exporter-native | cadvisor | Infrastructure | container CPU | SRE |
| `container_memory_working_set_bytes` | gauge | bytes | exporter-native | cadvisor | Infrastructure | container memory | SRE |
| `node_cpu_seconds_total` | counter | seconds | exporter-native | node-exporter | Infrastructure | host CPU | SRE |
| `node_memory_MemAvailable_bytes` | gauge | bytes | exporter-native | node-exporter | Infrastructure | host memory | SRE |
| `pg_up` | gauge | total | exporter-native | postgres-exporter | Infrastructure | database availability | SRE/DBA |
| `pg_stat_database_xact_commit` | counter | total | exporter-native | postgres-exporter | Infrastructure | DB throughput | SRE/DBA |
| `pg_stat_database_deadlocks` | counter | total | exporter-native | postgres-exporter | Infrastructure | deadlock alerting | SRE/DBA |
| `redis_up` | gauge | total | exporter-native | redis-exporter | Infrastructure | cache availability | SRE |
| `redis_memory_used_bytes` | gauge | bytes | exporter-native | redis-exporter | Infrastructure | cache saturation | SRE |
| `redis_connected_clients` | gauge | total | exporter-native | redis-exporter | Infrastructure | client saturation | SRE |

---

## 12. Derived Metrics And Recording Rules

The following should be produced as derived queries or recording rules rather than raw per-event metrics by default:

- API error rate;
- bootstrap error rate;
- application submit conversion;
- median time to first review;
- p95 review age;
- needs-info rate;
- rejection rate by reason;
- attribution no-owner rate;
- postback success rate;
- refund rate;
- chargeback rate;
- case SLA breach rate;
- payout liability aggregates;
- outbox lag percentiles.

---

## 13. Catalog Acceptance Conditions

This catalog is acceptable only when:

- each major partner platform domain has baseline metrics;
- every metric keeps to bounded label policy;
- no per-entity identifiers appear in labels;
- finance, compliance, admin, worker, and infra signals are all represented;
- dashboards and alerts can be built from this catalog without guessing new metric names.
