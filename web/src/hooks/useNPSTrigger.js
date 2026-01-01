/**
 * useNPSTrigger - Custom hook for NPS survey trigger and rate limit logic
 *
 * This hook manages the NPS survey lifecycle:
 * - Checks if survey should be shown based on trigger type and rate limiting
 * - Handles survey submission and dismissal
 * - Prevents surveys during critical operations
 * - Only triggers for authenticated users
 */
import { useCallback, useEffect, useRef } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import {
  checkShouldShow,
  submitNPS,
  dismissNPS,
  openSurvey,
  closeSurvey,
  setScore,
  setComment,
  resetSurvey,
  selectNPSIsOpen,
  selectNPSTriggerType,
  selectNPSScore,
  selectNPSComment,
  selectNPSShouldShow,
  selectNPSShouldShowLoading,
  selectNPSSubmitting,
  selectNPSSubmitSuccess,
  selectNPSSubmitError,
} from '../store/slices/npsSlice'
import { selectIsAuthenticated } from '../store/slices/authSlice'

/**
 * Valid trigger types for NPS surveys
 */
export const NPS_TRIGGER_TYPES = {
  FIRST_DEPLOYMENT: 'first_deployment',
  MONTHLY: 'monthly',
  ISSUE_RESOLUTION: 'issue_resolution',
}

/**
 * Hook for managing NPS survey triggers and rate limiting
 *
 * @param {Object} options - Configuration options
 * @param {string} options.triggerType - The type of trigger to check (from NPS_TRIGGER_TYPES)
 * @param {boolean} options.autoCheck - Whether to auto-check on mount (default: false)
 * @param {boolean} options.checkOnAuth - Whether to check when user becomes authenticated (default: false)
 * @returns {Object} NPS trigger state and handlers
 */
const useNPSTrigger = (options = {}) => {
  const {
    triggerType = NPS_TRIGGER_TYPES.MONTHLY,
    autoCheck = false,
    checkOnAuth = false,
  } = options

  const dispatch = useDispatch()
  const hasCheckedRef = useRef(false)

  // Auth state
  const isAuthenticated = useSelector(selectIsAuthenticated)

  // NPS state
  const isOpen = useSelector(selectNPSIsOpen)
  const currentTriggerType = useSelector(selectNPSTriggerType)
  const score = useSelector(selectNPSScore)
  const comment = useSelector(selectNPSComment)
  const shouldShow = useSelector(selectNPSShouldShow)
  const loading = useSelector(selectNPSShouldShowLoading)
  const submitting = useSelector(selectNPSSubmitting)
  const submitSuccess = useSelector(selectNPSSubmitSuccess)
  const submitError = useSelector(selectNPSSubmitError)

  /**
   * Check if the NPS survey should be shown for the given trigger type
   * Only checks if user is authenticated
   */
  const checkTrigger = useCallback(
    async (overrideTriggerType) => {
      const typeToCheck = overrideTriggerType || triggerType

      if (!isAuthenticated) {
        return { show: false, reason: 'not_authenticated' }
      }

      try {
        const result = await dispatch(
          checkShouldShow({ triggerType: typeToCheck })
        ).unwrap()
        return result
      } catch (error) {
        return { show: false, reason: 'error', error }
      }
    },
    [dispatch, triggerType, isAuthenticated]
  )

  /**
   * Manually trigger the NPS survey to open
   * Bypasses rate limiting check (useful for testing or admin override)
   */
  const triggerSurvey = useCallback(
    (overrideTriggerType) => {
      if (!isAuthenticated) {
        return false
      }

      dispatch(
        openSurvey({ triggerType: overrideTriggerType || triggerType })
      )
      return true
    },
    [dispatch, triggerType, isAuthenticated]
  )

  /**
   * Handle survey dismissal
   * Records the dismissal for rate limiting purposes
   */
  const handleDismiss = useCallback(async () => {
    if (!currentTriggerType) {
      dispatch(closeSurvey())
      return
    }

    try {
      await dispatch(dismissNPS({ triggerType: currentTriggerType })).unwrap()
    } catch (error) {
      // Still close the survey even if recording dismissal fails
      dispatch(closeSurvey())
    }
  }, [dispatch, currentTriggerType])

  /**
   * Handle score selection
   */
  const handleScoreChange = useCallback(
    (newScore) => {
      if (newScore >= 0 && newScore <= 10) {
        dispatch(setScore(newScore))
      }
    },
    [dispatch]
  )

  /**
   * Handle comment change
   */
  const handleCommentChange = useCallback(
    (newComment) => {
      dispatch(setComment(newComment))
    },
    [dispatch]
  )

  /**
   * Handle survey submission
   * Validates score and submits to the API
   */
  const handleSubmit = useCallback(async () => {
    if (score === null || score < 0 || score > 10) {
      return { success: false, error: 'Invalid score' }
    }

    try {
      const result = await dispatch(
        submitNPS({
          score,
          comment: comment || null,
          triggerType: currentTriggerType || triggerType,
        })
      ).unwrap()
      return { success: true, result }
    } catch (error) {
      return { success: false, error }
    }
  }, [dispatch, score, comment, currentTriggerType, triggerType])

  /**
   * Reset the survey state
   */
  const reset = useCallback(() => {
    dispatch(resetSurvey())
  }, [dispatch])

  /**
   * Close the survey without recording a dismissal
   */
  const close = useCallback(() => {
    dispatch(closeSurvey())
  }, [dispatch])

  // Auto-check on mount if enabled
  useEffect(() => {
    if (autoCheck && isAuthenticated && !hasCheckedRef.current) {
      hasCheckedRef.current = true
      checkTrigger()
    }
  }, [autoCheck, isAuthenticated, checkTrigger])

  // Check when authentication status changes if enabled
  useEffect(() => {
    if (checkOnAuth && isAuthenticated && !hasCheckedRef.current) {
      hasCheckedRef.current = true
      checkTrigger()
    }
  }, [checkOnAuth, isAuthenticated, checkTrigger])

  // Reset the checked flag when user logs out
  useEffect(() => {
    if (!isAuthenticated) {
      hasCheckedRef.current = false
    }
  }, [isAuthenticated])

  return {
    // State
    isOpen,
    shouldShow,
    loading,
    submitting,
    submitSuccess,
    submitError,
    score,
    comment,
    triggerType: currentTriggerType,
    isAuthenticated,

    // Actions
    checkTrigger,
    triggerSurvey,
    handleDismiss,
    handleSubmit,
    handleScoreChange,
    handleCommentChange,
    reset,
    close,
  }
}

export default useNPSTrigger
