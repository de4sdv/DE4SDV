// The AOSP adapter of the DE4SDV IVI frame relay to libsdvgatewayclient, the
// C API of the SDV Gateway on IVI
// (sdv_gateway/libsdvgatewayclient/include/libsdvgatewayclient.h of AOSP
// android17-release, manifest ad156f32).
//
// Only an AOSP build compiles this file: the DE4SDV CI has no AOSP tree, so
// it builds and tests the relay with the fake client of the tests instead.
// The VM session of phase 10 builds it with Android.bp.
//
// The adapter calls only these functions: ASDVGateway_Client_new,
// ASDVGateway_Client_setClientNotificationCallback,
// ASDVGateway_Client_initComms, ASDVGateway_Client_subscribeToPublicationByName
// (with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE),
// ASDVGateway_Client_setNotificationCallbackForPublicationId (to clear it),
// ASDVGateway_Client_unsubscribeFromPublication,
// ASDVGateway_Client_readAvailableMessages and ASDVGateway_Client_delete. It
// creates no publication and no RPC server. The callbacks run on the binder
// thread pool, which the constructor starts; they only hand the notification
// to the sink. Their user data is the generation of the client or of the
// subscription, so a late callback of an old one is told apart. The library
// allows one client per process (libsdvgatewayclient.h:473-475), so the
// adapter never deletes a client to create a new one: it deletes the client
// only at the stop of the relay.

#ifndef DE4SDV_IVI_FRAME_RELAY_SDV_GATEWAY_CLIENT_HPP
#define DE4SDV_IVI_FRAME_RELAY_SDV_GATEWAY_CLIENT_HPP

#include "de4sdv_ivi_frame_relay/gateway_client.hpp"

struct ASDVGateway_Client;

namespace de4sdv::ivi_frame_relay {

class SdvGatewayClient final : public GatewayClient {
 public:
  SdvGatewayClient();
  ~SdvGatewayClient() override;
  SdvGatewayClient(const SdvGatewayClient&) = delete;
  SdvGatewayClient& operator=(const SdvGatewayClient&) = delete;

  GatewayResult NewClient(std::uint64_t client_generation, GatewayNotificationSink& sink, bool* created) override;
  GatewayResult InitComms(const SubjectIdentity& subject) override;
  GatewayResult Destroy() override;
  GatewayResult Subscribe(std::uint64_t subscription_generation, const PublicationName& publication,
                          PublicationMetadata* metadata) override;
  GatewayResult Unsubscribe(std::int32_t publication_id) override;
  ReadResult Read(std::int32_t publication_id, std::uint8_t* buffer, std::size_t capacity) override;

 private:
  ASDVGateway_Client* client_{nullptr};
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_SDV_GATEWAY_CLIENT_HPP
