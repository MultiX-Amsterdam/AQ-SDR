#!/bin/bash
# Run data preparation scripts sequentially with logging

LOGFILE="run_data_preparation.log"

# Create/clear logfile at start
: > "$LOGFILE"

echo "=== Starting data preparation run: $(date) ===" | tee -a "$LOGFILE"

# First script
echo ">>> Running prepare_all_data.py" | tee -a "$LOGFILE"
python -u prepare_all_data.py \
  --eu_data "/home/yahia/aq-sdr/EU_data" \
  --final_dir "/home/yahia/final_dir_eudata" \
  --dummy_holder "/home/ssda/dummy_holder"  >> "$LOGFILE" 2>&1
STATUS1=$?

if [ $STATUS1 -eq 0 ]; then
    echo "✅ prepare_all_data.py completed successfully." | tee -a "$LOGFILE"
else
    echo "❌ prepare_all_data.py failed with exit code $STATUS1." | tee -a "$LOGFILE"
fi

# Second script (runs regardless of first’s status)
echo ">>> Running prepare_taiwan_data.py" | tee -a "$LOGFILE"
python -u prepare_taiwan_data.py \
  --operation_root "/home/yahia/aq-sdr/out_of_distribution_downloaded" \
  --final_root "/home/yahia/final_dir_ood"  >> "$LOGFILE" 2>&1
STATUS2=$?

if [ $STATUS2 -eq 0 ]; then
    echo "✅ prepare_taiwan_data.py completed successfully." | tee -a "$LOGFILE"
else
    echo "❌ prepare_taiwan_data.py failed with exit code $STATUS2." | tee -a "$LOGFILE"
fi

echo "=== Data preparation run finished: $(date) ===" | tee -a "$LOGFILE"
