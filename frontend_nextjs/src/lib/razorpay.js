/**
 * Razorpay Checkout loader + opener for escrow funding.
 * @see https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/
 */

export function loadRazorpayCheckout() {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("Razorpay Checkout is browser-only"));
      return;
    }
    if (window.Razorpay) {
      resolve(window.Razorpay);
      return;
    }
    const existing = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(window.Razorpay));
      existing.addEventListener("error", () => reject(new Error("Failed to load Razorpay Checkout")));
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(window.Razorpay);
    script.onerror = () => reject(new Error("Failed to load Razorpay Checkout script"));
    document.body.appendChild(script);
  });
}

/**
 * @param {object} order - RazorpayOrderResponse from backend
 * @param {object} opts
 * @param {string} opts.taskId
 * @param {function} [opts.onSuccess] - (razorpayResponse) => void
 * @param {function} [opts.onDismiss] - () => void
 */
export async function openRazorpayCheckout(order, { taskId, onSuccess, onDismiss }) {
  const Razorpay = await loadRazorpayCheckout();

  return new Promise((resolve, reject) => {
    const options = {
      key: order.key_id,
      amount: order.amount_paise,
      currency: order.currency || "INR",
      name: "VayuTask AI",
      description: `Escrow funding for task ${String(taskId).slice(0, 8)}…`,
      order_id: order.order_id,
      theme: { color: "#14b8a6" },
      handler(response) {
        onSuccess?.(response);
        resolve({ status: "success", response });
      },
      modal: {
        ondismiss() {
          onDismiss?.();
          resolve({ status: "dismissed" });
        },
      },
    };

    try {
      const instance = new Razorpay(options);
      instance.on("payment.failed", (response) => {
        reject(new Error(response?.error?.description || "Payment failed"));
      });
      instance.open();
    } catch (err) {
      reject(err);
    }
  });
}
