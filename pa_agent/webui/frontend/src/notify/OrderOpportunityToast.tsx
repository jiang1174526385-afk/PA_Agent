import { useEffect } from "react";

// Mirrors pa_agent/gui/order_opportunity.py::ORDER_ALERT_AUTO_CLOSE_MS -- the
// desktop non-modal QMessageBox auto-closes after the same duration.
const AUTO_CLOSE_MS = 120_000;

export interface OrderOpportunityToastProps {
  message: string;
  onClose: () => void;
}

/** Page-in-toast alert for a detected stage-2 order opportunity (see
 * phase-6-execution-plan.md §0.2 -- confirmed with the user: no browser
 * Notification API, no sound; page-only toast). */
export function OrderOpportunityToast({ message, onClose }: OrderOpportunityToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, AUTO_CLOSE_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message]);

  return (
    <div className="order-opportunity-toast" data-testid="order-opportunity-toast">
      <div className="order-opportunity-toast-title">🚨 下单机会</div>
      <pre className="order-opportunity-toast-body">{message}</pre>
      <button onClick={onClose}>关闭</button>
    </div>
  );
}
