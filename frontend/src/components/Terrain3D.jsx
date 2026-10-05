import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Html } from '@react-three/drei'
import * as THREE from 'three'

const PILLAR_ORDER = ['completeness', 'uniqueness', 'validity', 'consistency', 'timeliness',
  'accuracy', 'integrity', 'conformity', 'freshness', 'traceability']
const RADIUS = 3.6
const SIGMA = 1.55

function pillarPosition(index) {
  const theta = (index / PILLAR_ORDER.length) * Math.PI * 2
  return [Math.cos(theta) * RADIUS, Math.sin(theta) * RADIUS]
}

function severityColor(score) {
  if (score >= 90) return new THREE.Color('#0ca30c')
  if (score >= 75) return new THREE.Color('#65a30d')
  if (score >= 55) return new THREE.Color('#fab219')
  if (score >= 35) return new THREE.Color('#ec835a')
  return new THREE.Color('#d03b3b')
}

function Terrain({ scores }) {
  const meshRef = useRef()
  const growRef = useRef(0)

  const { geometry, peaks } = useMemo(() => {
    const geo = new THREE.PlaneGeometry(12, 12, 110, 110)
    geo.rotateX(-Math.PI / 2)
    const heights = PILLAR_ORDER.map((p) => ((scores[p] ?? 100) / 100) * 2.6)
    const centers = PILLAR_ORDER.map((_, i) => pillarPosition(i))
    const pos = geo.attributes.position
    const colors = new Float32Array(pos.count * 3)
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i)
      const z = pos.getZ(i)
      let h = 0
      for (let p = 0; p < centers.length; p++) {
        const dx = x - centers[p][0]
        const dz = z - centers[p][1]
        h += heights[p] * Math.exp(-(dx * dx + dz * dz) / (2 * SIGMA * SIGMA))
      }
      pos.setY(i, h)
      const c = severityColor(h / 2.6 * 100)
      colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.computeVertexNormals()
    const peakList = PILLAR_ORDER.map((p, i) => ({
      name: p, score: scores[p] ?? 100, x: centers[i][0], z: centers[i][1], y: heights[i],
    }))
    return { geometry: geo, peaks: peakList }
  }, [scores])

  useFrame((_, delta) => {
    growRef.current = Math.min(1, growRef.current + delta * 0.8)
    const eased = 1 - Math.pow(1 - growRef.current, 3)
    if (meshRef.current) meshRef.current.scale.y = Math.max(0.001, eased)
  })

  return (
    <group>
      <mesh ref={meshRef} geometry={geometry}>
        <meshStandardMaterial vertexColors roughness={0.45} metalness={0.1} flatShading={false} />
      </mesh>
      {peaks.map((p) => (
        <Html key={p.name} position={[p.x, p.y + 0.9, p.z]} center distanceFactor={12} zIndexRange={[10, 0]}>
          <div className="px-2 py-0.5 rounded-md text-[10px] font-bold whitespace-nowrap bg-surface/90 border border-border text-text shadow">
            {p.name.charAt(0).toUpperCase() + p.name.slice(1)} · {p.score}
          </div>
        </Html>
      ))}
    </group>
  )
}

function IssueOrbs({ issues, scores }) {
  const orbs = useMemo(() => {
    const top = [...issues]
      .filter((i) => i.pillar && i.pillar !== 'N/A')
      .sort((a, b) => (b.impact_score || 0) - (a.impact_score || 0))
      .slice(0, 12)
    return top.map((issue, idx) => {
      const key = issue.pillar.toLowerCase()
      const p = PILLAR_ORDER.indexOf(key)
      const [cx, cz] = p >= 0 ? pillarPosition(p) : [0, 0]
      const baseH = p >= 0 ? ((scores[key] ?? 100) / 100) * 2.6 : 0
      const angle = idx * 0.9
      return {
        id: issue.issue_id,
        label: `${issue.issue_type} · ${issue.column || 'dataset'}`,
        impact: issue.impact_score || 0,
        position: [cx + Math.cos(angle) * 0.7, baseH + 1.2 + (issue.impact_score || 0) / 40, cz + Math.sin(angle) * 0.7],
        radius: 0.12 + (issue.impact_score || 0) / 160,
      }
    })
  }, [issues, scores])

  return (
    <>
      {orbs.map((o, i) => <Orb key={o.id} {...o} phase={i} showLabel={i < 5} />)}
    </>
  )
}

function Orb({ position, radius, impact, label, phase, showLabel }) {
  const ref = useRef()
  useFrame(({ clock }) => {
    if (ref.current) ref.current.position.y = position[1] + Math.sin(clock.elapsedTime * 1.4 + phase) * 0.12
  })
  const color = impact >= 15 ? '#d03b3b' : impact >= 8 ? '#fab219' : '#2a78d6'
  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[radius, 24, 24]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} roughness={0.2} metalness={0.3} />
      {showLabel && (
        <Html center distanceFactor={14} zIndexRange={[5, 0]} style={{ pointerEvents: 'none' }}>
          <div className="text-[9px] text-text whitespace-nowrap opacity-80">{label}</div>
        </Html>
      )}
    </mesh>
  )
}

export default function Terrain3D({ pillarScores, issues }) {
  return (
    <div className="w-full h-[420px] rounded-xl overflow-hidden border border-border bg-gradient-to-b from-surface to-surface-raised">
      <Canvas camera={{ position: [12, 11, 12], fov: 40 }} dpr={[1, 2]}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[6, 10, 4]} intensity={1.1} />
        <pointLight position={[-6, 6, -4]} intensity={0.6} color="#2a78d6" />
        <Terrain scores={pillarScores} />
        <IssueOrbs issues={issues} scores={pillarScores} />
        <OrbitControls enablePan={false} autoRotate autoRotateSpeed={0.6} minDistance={7} maxDistance={22} />
      </Canvas>
      <div className="absolute mt-[-28px] ml-3 text-[11px] text-text-secondary pointer-events-none">
        Drag to orbit · scroll to zoom
      </div>
    </div>
  )
}
