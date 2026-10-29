{% macro delinquency_bucket(dpd_col) -%}
    case
        when {{ dpd_col }} = 0 then 'CURRENT'
        when {{ dpd_col }} < 60 then 'DPD_30'
        when {{ dpd_col }} < 90 then 'DPD_60'
        when {{ dpd_col }} < 180 then 'DPD_90_PLUS'
        else 'DEFAULT'
    end
{%- endmacro %}
