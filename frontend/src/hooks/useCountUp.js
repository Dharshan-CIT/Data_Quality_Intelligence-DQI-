import { useEffect, useRef, useState } from 'react'

/** Animates a number from its previous value to `target` over `duration` ms. */
export function useCountUp(target, duration = 600, decimals = 0) {
  const [value, setValue] = useState(target)
  const prevRef = useRef(target)
  const frameRef = useRef(null)

  useEffect(() => {
    const from = prevRef.current
    const to = typeof target === 'number' && !Number.isNaN(target) ? target : 0
    const start = performance.now()

    function step(now) {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(from + (to - from) * eased)
      if (t < 1) {
        frameRef.current = requestAnimationFrame(step)
      } else {
        prevRef.current = to
      }
    }
    frameRef.current = requestAnimationFrame(step)

    // requestAnimationFrame is only serviced while the page is actively
    // compositing frames — a backgrounded/occluded tab can stall it
    // indefinitely. This timer is a correctness floor: it guarantees the
    // displayed value reaches the real target even if rAF never fires.
    const fallback = setTimeout(() => { setValue(to); prevRef.current = to }, duration + 50)

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
      clearTimeout(fallback)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target])

  return decimals > 0 ? value.toFixed(decimals) : Math.round(value).toLocaleString()
}
