-- Portfolio KPIs per month x product x credit tier: balances, delinquency rates, roll rates.
select
    reporting_month,
    product,
    credit_tier,
    count(*)                                                              as active_loans,
    round(sum(upb), 2)                                                    as total_upb,
    round(sum(case when dq_bucket <> 'CURRENT' then upb else 0 end), 2)   as delinquent_upb,
    round(avg(case when dq_bucket <> 'CURRENT' then 1.0 else 0 end), 4)   as dq_rate_count,
    round(sum(case when dq_bucket <> 'CURRENT' then upb else 0 end)
          / nullif(sum(upb), 0), 4)                                       as dq_rate_upb,
    sum(case when dq_bucket = 'DPD_90_PLUS' or dq_bucket = 'DEFAULT' then 1 else 0 end) as seriously_dq_loans,
    round(
        sum(case when prior_dq_bucket = 'CURRENT' and dq_bucket = 'DPD_30' then 1.0 else 0 end)
        / nullif(sum(case when prior_dq_bucket = 'CURRENT' then 1 else 0 end), 0), 4
    )                                                                     as roll_rate_current_to_30
from {{ ref('int_loan_month_status') }}
group by 1, 2, 3
