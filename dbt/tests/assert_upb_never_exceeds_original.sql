-- Unpaid principal can grow only slightly via capitalised interest; flag anything > 105% of original.
select s.loan_id, s.reporting_month, s.upb, l.original_balance
from {{ ref('stg_servicing') }} s
join {{ ref('stg_loans') }} l using (loan_id)
where s.upb > l.original_balance * 1.05
