import Capacitor

class OptiPleinViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        super.capacitorDidLoad()
        bridge?.registerPluginInstance(OptiPleinPurchasesPlugin())
    }
}
