import React, { useEffect, useState, useRef } from "react";

/**
 * High-performance, glitch-free Typewriter effect.
 * Uses a single deterministic state machine without nested timeouts or re-render collisions.
 */
export function Typewriter({
  words = [
    "Expired Medicines",
    "Missed Reorders",
    "Low-Stock Surprises",
  ],
  speed = 80,
  deleteSpeed = 45,
  delayBetweenWords = 2200,
  cursor = true,
  cursorChar = "|",
  cursorClassName = "text-[#F26A4B]",
  className = "",
}) {
  const [displayText, setDisplayText] = useState("");
  const [showCursor, setShowCursor] = useState(true);

  // Keep state in refs so timers always read the latest tick without triggering stale closures
  const stateRef = useRef({
    wordIndex: 0,
    isDeleting: false,
    text: "",
  });

  useEffect(() => {
    if (!words || words.length === 0) return;

    let timer = null;

    const tick = () => {
      const { wordIndex, isDeleting, text } = stateRef.current;
      const targetWord = words[wordIndex % words.length] || "";

      if (!isDeleting) {
        // Typing characters forward
        if (text.length < targetWord.length) {
          const nextText = targetWord.slice(0, text.length + 1);
          stateRef.current.text = nextText;
          setDisplayText(nextText);
          timer = setTimeout(tick, speed);
        } else {
          // Word is completely typed — pause before deleting
          stateRef.current.isDeleting = true;
          timer = setTimeout(tick, delayBetweenWords);
        }
      } else {
        // Deleting characters backward
        if (text.length > 0) {
          const nextText = targetWord.slice(0, text.length - 1);
          stateRef.current.text = nextText;
          setDisplayText(nextText);
          timer = setTimeout(tick, deleteSpeed);
        } else {
          // Word is completely deleted — move to next word and start typing
          stateRef.current.isDeleting = false;
          stateRef.current.wordIndex = (wordIndex + 1) % words.length;
          timer = setTimeout(tick, speed);
        }
      }
    };

    // Kick off typing initial word
    timer = setTimeout(tick, speed);

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [words, speed, deleteSpeed, delayBetweenWords]);

  // Smooth cursor blinking
  useEffect(() => {
    if (!cursor) return;
    const cursorTimer = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);
    return () => clearInterval(cursorTimer);
  }, [cursor]);

  return (
    <span className={`inline-block ${className}`}>
      <span>{displayText}</span>
      {cursor && (
        <span
          className={`ml-0.5 font-light ${cursorClassName || "text-[#F26A4B]"} select-none inline-block align-baseline`}
          style={{
            opacity: showCursor ? 1 : 0,
            transition: "opacity 0.08s ease-in-out",
          }}
          aria-hidden="true"
        >
          {cursorChar}
        </span>
      )}
    </span>
  );
}
