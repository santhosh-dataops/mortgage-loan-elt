with last_status as (
    select loan_id, reporting_month, upb, dq_bucket,
           row_number() over (partition by loan_id order by reporting_month desc) as rn
    from {{ ref('int_loan_month_status') }}
),

ever_dq as (
    select loan_id, max(days_past_due) as max_dpd
    from {{ ref('int_loan_month_status') }}
    group by 1
)

select
    l.loan_id,
    l.borrower_id,
    l.origination_date,
    l.product,
    l.loan_purpose,
    l.property_state,
    l.credit_score,
    l.credit_tier,
    l.ltv,
    l.dti,
    l.interest_rate,
    l.original_balance,
    ls.reporting_month       as last_reported_month,
    ls.upb                   as current_upb,
    ls.dq_bucket             as current_status,
    coalesce(e.max_dpd, 0)   as max_days_past_due,
    coalesce(e.max_dpd, 0) >= 90 as ever_90_plus
from {{ ref('stg_loans') }} l
left join last_status ls on ls.loan_id = l.loan_id and ls.rn = 1
left join ever_dq e on e.loan_id = l.loan_id
