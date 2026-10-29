-- Loan-month grain with delinquency state and roll-rate transition vs. prior month.
with s as (
    select
        sv.*,
        {{ delinquency_bucket('sv.days_past_due') }} as dq_bucket
    from {{ ref('stg_servicing') }} sv
)

select
    s.loan_id,
    s.reporting_month,
    s.upb,
    s.days_past_due,
    s.dq_bucket,
    lag(s.dq_bucket) over (partition by s.loan_id order by s.reporting_month) as prior_dq_bucket,
    s.actual_payment = 0 as missed_payment,
    l.product,
    l.credit_tier,
    l.property_state,
    l.original_balance
from s
join {{ ref('stg_loans') }} l using (loan_id)
