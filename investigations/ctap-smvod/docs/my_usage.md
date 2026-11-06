1. Download all the csv from lighstep
2. python3 scripts/run_pipeline.py --date 08102026 python3 scripts/run_pipeline.py --date 23102026 --drm
3. python extract_error_report_1xxx_6xxx.py --from 12102026 --to 1102026 --output-dir ../output/SA
4. copy it to ~/Documents/1xxx
5. Send mail in "Re: [PRB0069729][INC0254164][MTN][SA]: VSF and EBVS with 1001 & 1003"
6. # one date -> output/<TENANT>/YYYY-MM-DD_error_report_1xxx.csv per tenant python scripts/extract_error_report_1xxx.py --date 21102026

# date range -> one .xlsx per tenant, one sheet per date
python3 extract_error_report_1xxx.py --from 12102026 --to 13102026 --tenants SA,GH

python3 rank_households_by_error.py --xlsx <path> --top N [MTN SA] CI & DFE Dashboard

python3 rank_households_by_error.py \
    --xlsx ../output/ZM/2026-10-01_2026-10-14_error_report_1xxx.xlsx \
    --top 10

for t in ZA GH ZM; do echo "== $t"; python scripts/rank_households_by_error.py --csv output/$t/2026-10-26_error_report_1xxx.csv --top 10; done

for t in ZA GH ZM; do echo "== $t"; python3 scripts/rank_households_by_error.py --csv output/$t/2026-10-21_error_report_1xxx_6xxx.csv --top 10; done python3 check_lightstep_inputs.py --date 27102026
--drm python scripts/run_pipeline.py --date 27102026 --drm python scripts/run_pipeline.py --date 21102026 --drm

for o in ZA GH ZM; do python investigations/ctap-smvod/scripts/analyze_drm_funnel.py --opco $o --date 2026-10-23 done

python3 scripts/check_lightstep_inputs.py --date 29102026 --drm python scripts/run_pipeline.py --date 29102026 --drm --skip-input-check python scripts/extract_error_report_1xxx.py --date 29102026 for
t in ZA GH ZM; do echo "== $t"; python scripts/rank_households_by_error.py --csv output/$t/2026-10-29_error_report_1xxx.csv --top 10; done


South Africa

Household ID rD_saW-tErOcf5IAOB8WUzjolkg7f11kmFW_ZufEMMgj3kDqciW8

Device ID f1062d7bc72d63370850d70f6407d525d319774d5f7f030ef886480e6a4de057

App Version v2026.09.16.02

Home TV Shows Movies Kids

v2026.09.16.02

07:59

2026-10-29_ctap.csv 2026-10-29_smvod.csv 2026-10-29_smvod-ts.csv 2026-10-29_mdrmfe.csv

07:59 AM

2026-10-29_mdrm-cdm-widevine.csv 2026-10-29_mdrm-cdm-fairplay.csv 2026-10-29_mdrm-cdm-playready.csv 2026-10-29_mdrm-lrm.csv



python -m src.lib.token_gen.cli G6YqLZHrv1O_3ol_pYaa0MQ5g3wQNJSPFZ3vD6H26xX5QIOqhmMb

python -m src.lib.token_gen.cli <householdID> [--expires-in 3600] [--json]


REPO=/Users/abhadra/myWork/myOffice/ih-trace-lab PY=/Users/abhadra/myWork/myOffice/ih-trace-lab/.venv/bin/python3 LOGS=/Users/abhadra/myWork/myOffice/ih-trace-lab/logs

0 13 * * * cd /Users/abhadra/myWork/myOffice/ih-trace-lab && .venv/bin/python investigations/ctap-smvod/scripts/run_daily_pipeline.py --date "$(date -v-2d +\%Y-\%m-\%d)" >>
investigations/ctap-smvod/logs/cron.out 2>&1

0 13 * * * cd $REPO && $PY investigations/ctap-smvod/scripts/run_daily_pipeline.py --date "$(date -v-2d +\%Y-\%m-\%d)" >> $LOGS/cron_daily_pipeline_.out 2>&1 cd $REPO && $PY -m
src.pipelines.aws_access_cli.scripts.run_daily_reports --date "$(date -v-1d +\%Y-\%m-\%d)" >> $LOGS/cron_daily_reports_v2.out 2>&1

for i in {1..20}; do echo "=== run $i ==="; python -m src.lib.token_gen.cli "apple|001170.db5c67668bb94e4ab2dee1df059d4969.0952"; done > logs/token.txt 2>&1