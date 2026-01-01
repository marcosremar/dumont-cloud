import { useState, useEffect } from 'react'
import { MessageSquare, Send, ThumbsUp, ThumbsDown, Meh, X } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'
import { Button } from './ui/button'
import { Label } from './ui/label'

/**
 * Get the category label and color based on NPS score
 * @param {number} score - NPS score (0-10)
 * @returns {{ label: string, color: string, icon: React.ComponentType }} Category info
 */
const getScoreCategory = (score) => {
  if (score === null) return null
  if (score <= 6) {
    return {
      label: 'Detractor',
      color: 'text-red-400',
      bgColor: 'bg-red-500/10 border-red-500/30',
      Icon: ThumbsDown,
    }
  }
  if (score <= 8) {
    return {
      label: 'Passive',
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/10 border-yellow-500/30',
      Icon: Meh,
    }
  }
  return {
    label: 'Promoter',
    color: 'text-green-400',
    bgColor: 'bg-green-500/10 border-green-500/30',
    Icon: ThumbsUp,
  }
}

/**
 * NPSSurvey Modal Component
 *
 * Displays a Net Promoter Score survey modal with:
 * - 0-10 score selection buttons
 * - Optional comment textarea
 * - Submit and dismiss buttons
 * - Loading state during submission
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Controls modal visibility
 * @param {function} props.onClose - Callback to close modal (without recording)
 * @param {function} props.onDismiss - Callback to dismiss survey (records dismissal)
 * @param {function} props.onSubmit - Callback to submit survey
 * @param {number|null} props.score - Currently selected score
 * @param {function} props.onScoreChange - Callback when score changes
 * @param {string} props.comment - Current comment text
 * @param {function} props.onCommentChange - Callback when comment changes
 * @param {boolean} props.submitting - Whether submission is in progress
 * @param {string|null} props.error - Error message to display
 * @param {string} props.triggerType - The trigger type for context
 */
export default function NPSSurvey({
  isOpen,
  onClose,
  onDismiss,
  onSubmit,
  score,
  onScoreChange,
  comment,
  onCommentChange,
  submitting = false,
  error = null,
  triggerType = null,
}) {
  const [localScore, setLocalScore] = useState(null)
  const [localComment, setLocalComment] = useState('')

  // Use props if provided, otherwise use local state
  const currentScore = score !== undefined ? score : localScore
  const currentComment = comment !== undefined ? comment : localComment

  const handleScoreChange = (newScore) => {
    if (onScoreChange) {
      onScoreChange(newScore)
    } else {
      setLocalScore(newScore)
    }
  }

  const handleCommentChange = (newComment) => {
    if (onCommentChange) {
      onCommentChange(newComment)
    } else {
      setLocalComment(newComment)
    }
  }

  // Reset local state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setLocalScore(null)
      setLocalComment('')
    }
  }, [isOpen])

  const handleSubmit = async () => {
    if (currentScore === null) return

    if (onSubmit) {
      await onSubmit()
    }
  }

  const handleDismiss = () => {
    if (onDismiss) {
      onDismiss()
    } else if (onClose) {
      onClose()
    }
  }

  const category = getScoreCategory(currentScore)
  const isValid = currentScore !== null

  return (
    <Dialog open={isOpen} onOpenChange={handleDismiss}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <MessageSquare className="w-5 h-5 text-brand-400" />
            How likely are you to recommend us?
          </DialogTitle>
          <DialogDescription className="text-gray-400">
            Your feedback helps us improve Dumont Cloud for everyone.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Error Display */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 flex items-start gap-2">
              <X className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {/* Score Selection */}
          <div className="space-y-3">
            <Label className="text-base font-medium text-white">
              Select a score from 0 to 10
            </Label>
            <div className="flex justify-between gap-1">
              {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((value) => {
                const isSelected = currentScore === value
                let buttonClass = 'transition-all duration-150 '

                if (isSelected) {
                  if (value <= 6) {
                    buttonClass += 'bg-red-500 text-white border-red-500 ring-2 ring-red-500/50'
                  } else if (value <= 8) {
                    buttonClass += 'bg-yellow-500 text-white border-yellow-500 ring-2 ring-yellow-500/50'
                  } else {
                    buttonClass += 'bg-green-500 text-white border-green-500 ring-2 ring-green-500/50'
                  }
                } else {
                  buttonClass += 'bg-gray-800/50 border-gray-700 hover:bg-gray-700/50 hover:border-gray-600 text-gray-300'
                }

                return (
                  <button
                    key={value}
                    type="button"
                    onClick={() => handleScoreChange(value)}
                    disabled={submitting}
                    className={`
                      w-10 h-10 rounded-lg border text-sm font-medium
                      focus:outline-none focus:ring-2 focus:ring-brand-500/50
                      disabled:opacity-50 disabled:cursor-not-allowed
                      ${buttonClass}
                    `}
                    aria-label={`Score ${value}`}
                    aria-pressed={isSelected}
                  >
                    {value}
                  </button>
                )
              })}
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>Not at all likely</span>
              <span>Extremely likely</span>
            </div>
          </div>

          {/* Score Category Feedback */}
          {category && (
            <div className={`rounded-lg border p-3 ${category.bgColor}`}>
              <div className="flex items-center gap-2">
                <category.Icon className={`w-4 h-4 ${category.color}`} />
                <span className={`text-sm font-medium ${category.color}`}>
                  {category.label}
                </span>
                <span className="text-sm text-gray-400">
                  {currentScore <= 6 && "- We'd love to know how we can improve"}
                  {currentScore >= 7 && currentScore <= 8 && '- Thanks for your honest feedback'}
                  {currentScore >= 9 && "- We're thrilled you love our service!"}
                </span>
              </div>
            </div>
          )}

          {/* Comment Section */}
          <div className="space-y-3">
            <Label className="text-base font-medium text-white flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-400" />
              Additional comments
              <span className="text-gray-500 font-normal">(optional)</span>
            </Label>
            <textarea
              value={currentComment}
              onChange={(e) => handleCommentChange(e.target.value)}
              placeholder={
                currentScore !== null && currentScore <= 6
                  ? 'What could we do better?'
                  : 'Tell us more about your experience...'
              }
              disabled={submitting}
              rows={3}
              maxLength={1000}
              className="
                w-full px-3 py-2
                bg-gray-900 border border-gray-700 rounded-lg
                text-white placeholder-gray-500
                focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500/50
                disabled:opacity-50 disabled:cursor-not-allowed
                resize-none
              "
            />
            <div className="flex justify-end text-xs text-gray-500">
              {currentComment.length}/1000
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            variant="ghost"
            onClick={handleDismiss}
            disabled={submitting}
            className="text-gray-400 hover:text-white"
          >
            Maybe later
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!isValid || submitting}
            className="bg-brand-500 hover:bg-brand-600 text-white gap-2"
          >
            <Send className="w-4 h-4" />
            {submitting ? 'Sending...' : 'Send feedback'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Standalone NPS Survey component that manages its own state
 * Use this when you want to control the survey independently
 */
export function NPSSurveyStandalone({
  isOpen,
  onClose,
  onSubmit,
  triggerType,
}) {
  const [score, setScore] = useState(null)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setScore(null)
      setComment('')
      setError(null)
    }
  }, [isOpen])

  const handleSubmit = async () => {
    if (score === null) return

    setSubmitting(true)
    setError(null)

    try {
      if (onSubmit) {
        await onSubmit({ score, comment: comment || null, triggerType })
      }
    } catch (err) {
      setError(err.message || 'Failed to submit feedback. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <NPSSurvey
      isOpen={isOpen}
      onClose={onClose}
      onDismiss={onClose}
      onSubmit={handleSubmit}
      score={score}
      onScoreChange={setScore}
      comment={comment}
      onCommentChange={setComment}
      submitting={submitting}
      error={error}
      triggerType={triggerType}
    />
  )
}
