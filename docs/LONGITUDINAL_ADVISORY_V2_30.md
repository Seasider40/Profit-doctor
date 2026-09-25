# v2.30 Longitudinal Advisory & Benefit Realisation

Profit Doctor now tracks advisory economics across repeated runs rather than treating each diagnostic as a new economic claim.

Controls include issue resolve/reopen history; stable opportunity keys across runs; prior realised claims deducted from updated expected opportunity; stale opportunity suppression; immutable benefit claim registry; and cross-client isolation. Verification and retention add evidence/state but do not create a second realised claim.

This layer deliberately does not infer persistence merely because a later period remains favourable: retention still requires explicit evidence.
