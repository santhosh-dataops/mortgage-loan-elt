select
    loan_id,
    cast(reporting_month as date)                    as reporting_month,
    cast(scheduled_payment as decimal(12, 2))        as scheduled_payment,
    cast(actual_payment as decimal(12, 2))           as actual_payment,
    cast(unpaid_principal_balance as decimal(14, 2)) as upb,
    cast(days_past_due as integer)                   as days_past_due
from {{ source('raw', 'loan_servicing') }}
