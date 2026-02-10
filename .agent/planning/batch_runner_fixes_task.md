# Batch Runner Bug Fixes

## Phase 1: Fix compliance_review Dict Issue
- [ ] Investigate compliance_review agent output format <!-- id: 1 -->
- [ ] Update script to handle dict output correctly <!-- id: 2 -->
- [ ] Re-test compliance_review for one topic <!-- id: 3 -->

## Phase 2: Fix Timeout Issues
- [ ] Increase timeout from 180s to 300s (5 min) <!-- id: 4 -->
- [ ] Add retry logic for timeouts <!-- id: 5 -->
- [ ] Re-test curriculum_design for failing topics <!-- id: 6 -->

## Phase 3: Add Resilience for Server Disconnects
- [ ] Add httpx retry logic with backoff <!-- id: 7 -->
- [ ] Handle connection errors gracefully <!-- id: 8 -->

## Phase 4: Re-run Failed Agents
- [ ] Re-run 2_hyperthyroid/curriculum_design <!-- id: 9 -->
- [ ] Re-run 5_polymyalgia/curriculum_design <!-- id: 10 -->
- [ ] Re-run 5_polymyalgia/marketing_plan <!-- id: 11 -->
- [ ] Re-run all compliance_review <!-- id: 12 -->
