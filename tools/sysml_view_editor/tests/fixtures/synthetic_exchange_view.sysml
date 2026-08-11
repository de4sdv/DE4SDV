/*
 * SYNTHETIC TEST MODEL — original test data for the editor pipeline.
 *
 * This file is NOT a copy of any DE4SDV model. It is a minimal hand-written
 * model that exercises the same editor features (view-driven sourcing, typed
 * ports and flows, source docs, payload labels) with no claim of mirroring
 * the middleware or any other real model. The authoritative middleware model
 * lives at textual-notation-of-model/.../mw_physical_software_realization.sysml
 * and is exercised by the integration gate after PR #90 merges.
 */
package DE4SDV_SyntheticExchangeFixture {

  /* Synthetic item types for the handoffs. */
  item def Request;
  item def Response;

  /* Port definitions carrying the typed payload features. */
  port def RequestPort {
    doc /* Synthetic request handoff between roles. */
    in out request : Request;
  }

  port def ResponsePort {
    doc /* Synthetic response handoff between roles. */
    in out response : Response;
  }

  /* Role part definitions. */
  part def SyntheticProducer {
    doc /* Synthetic producer role. Emits the request payload. */
    port requestOut : RequestPort;
  }

  part def SyntheticRelay {
    doc /* Synthetic relay role. Forwards the request and returns the response. */
    port requestIn : RequestPort;
    port responseOut : ResponsePort;
  }

  part def SyntheticConsumer {
    doc /* Synthetic consumer role. Receives the response payload. */
    port responseIn : ResponsePort;
  }

  part def SyntheticExchangeDeployment {
    doc /* Synthetic deployment exercising the editor pipeline. Not part of the middleware model. */
    part producer : SyntheticProducer;
    part relay : SyntheticRelay;
    part consumer : SyntheticConsumer;

    doc /* Synthetic request handoff from producer to relay. */
    flow from producer.requestOut.request
      to relay.requestIn.request;

    doc /* Synthetic response handoff from relay to consumer. */
    flow from relay.responseOut.response
      to consumer.responseIn.response;
  }

  part syntheticDeployment : SyntheticExchangeDeployment;

  view syntheticExchangeView {
    viewpoint selectedSyntheticExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame syntheticExchangeConcern;
    }
    expose syntheticDeployment;
    expose syntheticDeployment::**;
    attribute depth = -1;
    render asInterconnectionDiagram;
  }
}
