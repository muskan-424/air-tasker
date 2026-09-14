"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Star } from "lucide-react";
import { tasksAPI } from "@/lib/api";

function inr(value) {
  const n = Number(value);
  return Number.isFinite(n) ? `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}` : "—";
}

/**
 * Offers on a published task.
 * - Poster: compare offers (price, rating, message) and accept one.
 * - Anyone else: make, update or withdraw their own offer, with the fee breakdown shown live.
 */
export default function TaskOffersPanel({ task, isPoster, onChanged }) {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const range = task.task_schema?.suggestedPriceRange || {};
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState("");
  const [quote, setQuote] = useState(null);
  // Prefill the form once; later reloads must not overwrite what the user is typing.
  const formPrefilled = useRef(false);

  const myOffer = !isPoster ? offers.find((o) => o.status !== "WITHDRAWN") || null : null;

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await tasksAPI.listOffers(task.id);
      setOffers(Array.isArray(data) ? data : []);
      if (!isPoster && !formPrefilled.current) {
        formPrefilled.current = true;
        const mine = (data || [])[0];
        setAmount(String(mine?.amount ? Number(mine.amount) : range.max || range.min || ""));
        setMessage(mine?.message || "");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [task.id, isPoster, range.max, range.min]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (isPoster) return;
    const price = parseFloat(amount);
    if (!price || price <= 0) { setQuote(null); return; }
    const t = setTimeout(() => {
      tasksAPI.feeQuote(price).then(setQuote).catch(() => setQuote(null));
    }, 300);
    return () => clearTimeout(t);
  }, [amount, isPoster]);

  const run = async (id, fn) => {
    setBusyId(id);
    setError(null);
    try {
      await fn();
      await load();
      await onChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const submitOffer = () => {
    const price = parseFloat(amount);
    if (!price || price <= 0) { setError("Enter your price in INR"); return; }
    run("submit", () => tasksAPI.makeOffer(task.id, price, message.trim() || null));
  };

  const acceptOffer = (offer) => {
    const who = offer.tasker_display_name || "this tasker";
    if (!window.confirm(`Assign the task to ${who} for ${inr(offer.amount)}? Other offers will be declined.`)) return;
    run(offer.offer_id, () => tasksAPI.acceptOffer(task.id, offer.offer_id));
  };

  if (loading) {
    return <section className="offers"><Loader2 className="spin-icon" size={18} /> Loading offers…</section>;
  }

  return (
    <section className="offers">
      {isPoster ? (
        <>
          <h3>Offers {offers.length > 0 && <span className="count">{offers.length}</span>}</h3>
          {offers.length === 0 ? (
            <p className="muted">No offers yet. Taskers in your area will send their price here.</p>
          ) : (
            <ul className="offer-list">
              {offers.map((offer) => (
                <li key={offer.offer_id} className={`offer ${offer.status !== "PENDING" ? "offer-closed" : ""}`}>
                  <div className="offer-main">
                    <div className="offer-who">
                      <strong>{offer.tasker_display_name || "Tasker"}</strong>
                      {offer.tasker_rating_count > 0 ? (
                        <span className="rating"><Star size={12} /> {offer.tasker_rating_average?.toFixed(1)} ({offer.tasker_rating_count})</span>
                      ) : (
                        <span className="muted small">New tasker</span>
                      )}
                    </div>
                    {offer.message && <p className="offer-msg">{offer.message}</p>}
                    <p className="muted small">You pay {inr(offer.fees.poster_total)} incl. {inr(offer.fees.poster_fee)} service fee</p>
                  </div>
                  <div className="offer-side">
                    <span className="price">{inr(offer.amount)}</span>
                    {offer.status === "PENDING" ? (
                      <button
                        type="button"
                        className="btn-premium btn-teal"
                        onClick={() => acceptOffer(offer)}
                        disabled={busyId !== null}
                      >
                        {busyId === offer.offer_id ? "Accepting…" : "Accept"}
                      </button>
                    ) : (
                      <span className="status">{offer.status.toLowerCase()}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <>
          <h3>{myOffer?.status === "PENDING" ? "Your offer" : "Make an offer"}</h3>
          {myOffer?.status === "DECLINED" ? (
            <p className="muted">This task went to another tasker.</p>
          ) : (
            <div className="offer-form">
              <label>
                Your price (INR)
                <input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} />
              </label>
              <label>
                Message to the poster (optional)
                <textarea
                  rows={3}
                  maxLength={1000}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Experience, when you can start, what's included"
                />
              </label>
              {quote && (
                <p className="muted small">
                  You receive {inr(quote.tasker_payout)} after the {inr(quote.tasker_fee)} service fee.
                </p>
              )}
              <div className="row">
                <button type="button" className="btn-premium btn-saffron" onClick={submitOffer} disabled={busyId !== null}>
                  {busyId === "submit" ? "Sending…" : myOffer?.status === "PENDING" ? "Update offer" : "Send offer"}
                </button>
                {myOffer?.status === "PENDING" && (
                  <button
                    type="button"
                    className="btn-premium btn-outline"
                    onClick={() => run("withdraw", () => tasksAPI.withdrawOffer(task.id, myOffer.offer_id))}
                    disabled={busyId !== null}
                  >
                    Withdraw
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {error && <p className="err">{error}</p>}

      <style jsx>{`
        .offers { display: flex; flex-direction: column; gap: 12px; }
        h3 { font-size: 0.95rem; display: flex; align-items: center; gap: 8px; }
        .count { font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border-teal); color: var(--color-teal); }
        .offer-list { list-style: none; display: flex; flex-direction: column; gap: 10px; padding: 0; margin: 0; }
        .offer { display: flex; justify-content: space-between; gap: 16px; padding: 14px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); background: rgba(0,0,0,0.15); flex-wrap: wrap; }
        .offer-closed { opacity: 0.55; }
        .offer-main { display: flex; flex-direction: column; gap: 4px; min-width: 0; flex: 1 1 220px; }
        .offer-who { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .rating { display: inline-flex; align-items: center; gap: 4px; font-size: 0.78rem; color: var(--color-saffron); }
        .offer-msg { font-size: 0.86rem; line-height: 1.5; color: var(--color-text-main); overflow-wrap: anywhere; }
        .offer-side { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
        .price { font-size: 1.2rem; font-weight: 800; }
        .status { font-size: 0.75rem; text-transform: capitalize; color: var(--color-text-muted); }
        .offer-form { display: flex; flex-direction: column; gap: 10px; max-width: 420px; }
        .offer-form label { display: flex; flex-direction: column; gap: 4px; font-size: 0.82rem; color: var(--color-text-muted); }
        .offer-form input, .offer-form textarea { padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(0,0,0,0.2); color: var(--color-text-main); font: inherit; }
        .row { display: flex; gap: 10px; flex-wrap: wrap; }
        .muted { color: var(--color-text-muted); font-size: 0.88rem; }
        .small { font-size: 0.78rem; }
        .err { color: #fca5a5; font-size: 0.85rem; }
      `}</style>
    </section>
  );
}
