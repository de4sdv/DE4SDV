// Exit codes of the AutowareToSCORE adapter process (INC-MW-011). 0 is a
// clean stop on SIGTERM or SIGINT by the second LoLa rule. Every other code
// tells the Launch Manager that the component failed; none of them is above
// 125, so none looks like the end by a signal.

#ifndef DE4SDV_SCORE_ADAPTER_EXIT_CODES_HPP
#define DE4SDV_SCORE_ADAPTER_EXIT_CODES_HPP

namespace de4sdv::score_adapter::exit_code {

// A bad command line, or the mw::com configuration file cannot be read.
constexpr int kConfigurationError = 2;
// Rule 2: the speed proxy stayed subscribed after Unsubscribe(), so the
// process ends without destructors (destroying it aborts, GAP-MW-041).
constexpr int kStillSubscribed = 3;
// Rule 3: the frame skeleton could not be created or offered.
constexpr int kFrameOfferFailed = 4;
// mw::com refused the state handler, the receive handler or the
// subscription of the speed proxy. The adapter does not retry in the
// process; the Launch Manager sees the failure.
constexpr int kSpeedSubscribeFailed = 5;

}  // namespace de4sdv::score_adapter::exit_code

#endif  // DE4SDV_SCORE_ADAPTER_EXIT_CODES_HPP
