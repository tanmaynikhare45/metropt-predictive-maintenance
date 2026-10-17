import Card from './Card'

export default function TwinPlaceholder({ className }) {
  return (
    <Card className={className} title="Digital twin" subtitle="Coming in Phase 7">
      <div className="placeholder">
        Health index, what-if sliders, remaining useful life and maintenance advice will appear here.
      </div>
    </Card>
  )
}
