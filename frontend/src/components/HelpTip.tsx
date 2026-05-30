import './HelpTip.css'

export default function HelpTip({ text, left }: { text: string; left?: boolean }) {
  return (
    <span className="helptip-wrap">
      <span className="helptip-icon">?</span>
      <span className={`helptip-bubble${left ? ' helptip-bubble-left' : ''}`}>{text}</span>
    </span>
  )
}
