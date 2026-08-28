# DE4SDV INC-AEBS-010 board sepolicy fragment.
#
# Staged to vendor/de4sdv/aebs_visualization/sepolicy/ and appended to
# BOARD_SEPOLICY_DIRS by the sdv_ivi_cf BoardConfig (see
# device/google/sdv/sdv_ivi_base/BoardConfig.mk BOARD_SEPOLICY_DIRS pattern).
# A soong `sepolicy` property is not supported by this release (verified:
# "unrecognized property \"sepolicy\""), so the .te ships via this make path.

BOARD_VENDOR_SEPOLICY_DIRS += vendor/de4sdv/aebs_visualization/sepolicy
