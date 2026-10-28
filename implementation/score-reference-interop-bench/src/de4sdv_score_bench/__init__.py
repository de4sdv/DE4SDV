"""Pure evaluators of the S-CORE reference interoperability bench (INC-MW-011).

The modules here read raw run artifacts (gdb backtraces, the adapter's JSON
log lines, observer and provider records) and return verdicts. They import
neither ROS 2 nor S-CORE, so the bench tests run anywhere.
"""
