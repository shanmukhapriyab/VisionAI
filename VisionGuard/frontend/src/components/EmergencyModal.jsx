import { useEffect, useRef } from "react";

export default function EmergencyModal({ open, onClose, result, error, phoneNumber, lastMessage }) {
  const ref = useRef(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog ref={ref} className="modal" onClose={onClose} aria-labelledby="em-h">
      <h2 id="em-h">Emergency alert (prototype)</h2>
      <p className="modal-strong">
        This prototype does <u>not</u> contact anyone. In a real emergency, call your local emergency number now.
      </p>
      {phoneNumber && (
        <a className="btn btn-emergency btn-call" href={`tel:${phoneNumber.replace(/[^+\d]/g, "")}`}>
          Call {phoneNumber}
        </a>
      )}
      <p className="muted">
        {error
          ? `The event could not be saved to the backend: ${error}`
          : result
            ? `The event was recorded on this computer at ${new Date(result.created_at).toLocaleTimeString()}.`
            : "Recording event…"}
      </p>
      {lastMessage && <p className="muted">Last alert before you pressed the button: “{lastMessage}”</p>}
      <button className="btn btn-main" onClick={onClose} autoFocus>Close</button>
    </dialog>
  );
}
