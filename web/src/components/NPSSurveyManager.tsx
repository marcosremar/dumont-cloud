/**
 * NPS Survey Manager Component
 * Manages NPS survey display and submission
 */
import { useEffect } from 'react'
import NPSSurvey from './NPSSurvey'
import useNPSTrigger, { NPS_TRIGGER_TYPES } from '../hooks/useNPSTrigger'

export default function NPSSurveyManager() {
  const {
    isOpen,
    score,
    comment,
    triggerType,
    submitting,
    submitError,
    isAuthenticated,
    handleDismiss,
    handleSubmit,
    handleScoreChange,
    handleCommentChange,
    checkTrigger,
  } = useNPSTrigger({
    triggerType: NPS_TRIGGER_TYPES.MONTHLY,
    autoCheck: false,
    checkOnAuth: true,
  })

  // Check for monthly trigger when component mounts and user is authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const timer = setTimeout(() => {
        checkTrigger(NPS_TRIGGER_TYPES.MONTHLY)
      }, 5000)

      return () => clearTimeout(timer)
    }
  }, [isAuthenticated, checkTrigger])

  return (
    <NPSSurvey
      isOpen={isOpen}
      onClose={handleDismiss}
      onDismiss={handleDismiss}
      onSubmit={handleSubmit}
      score={score}
      onScoreChange={handleScoreChange}
      comment={comment}
      onCommentChange={handleCommentChange}
      submitting={submitting}
      error={submitError}
      triggerType={triggerType}
    />
  )
}
