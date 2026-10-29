select *
from {{ ref('fct_portfolio_monthly') }}
where dq_rate_count not between 0 and 1
   or dq_rate_upb not between 0 and 1
   or roll_rate_current_to_30 not between 0 and 1
