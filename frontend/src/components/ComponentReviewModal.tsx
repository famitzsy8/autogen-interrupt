/**
 * ComponentReviewModal - Modal for reviewing and editing AI-generated analysis components
 *
 * Allows users to:
 * - Review AI-generated components
 * - Edit component labels and descriptions
 * - Remove unwanted components
 * - Add new custom components
 * - Confirm and start run with approved components
 */

import React, { useState } from 'react'
import type { AnalysisComponent } from '../types'

interface ComponentReviewModalProps {
  components: AnalysisComponent[]
  trigger_threshold: number
  onApprove: (finalComponents: AnalysisComponent[]) => void
  onCancel: () => void
  isGenerating?: boolean
}

export function ComponentReviewModal({
  components,
  trigger_threshold,
  onApprove,
  onCancel,
  isGenerating = false,
}: ComponentReviewModalProps): React.ReactElement {
  const [editableComponents, setEditableComponents] = useState<AnalysisComponent[]>(components)
  const [isAddingNew, setIsAddingNew] = useState(false)
  const [newLabel, setNewLabel] = useState('')
  const [newDescription, setNewDescription] = useState('')

  const handleLabelChange = (index: number, newValue: string): void => {
    const updated = [...editableComponents]
    updated[index] = { ...updated[index], label: newValue }
    setEditableComponents(updated)
  }

  const handleDescriptionChange = (index: number, newValue: string): void => {
    const updated = [...editableComponents]
    updated[index] = { ...updated[index], description: newValue }
    setEditableComponents(updated)
  }

  const handleRemove = (index: number): void => {
    const updated = editableComponents.filter((_, i) => i !== index)
    setEditableComponents(updated)
  }

  const handleAddNew = (): void => {
    if (!newLabel.trim() || !newDescription.trim()) {
      alert('Please provide both a label and description')
      return
    }

    const newComponent: AnalysisComponent = {
      label: newLabel.trim(),
      description: newDescription.trim(),
      color: '#888888', // Default gray, will be assigned properly by backend
    }

    setEditableComponents([...editableComponents, newComponent])
    setNewLabel('')
    setNewDescription('')
    setIsAddingNew(false)
  }

  const handleApprove = (): void => {
    if (editableComponents.length === 0) {
      const confirmed = confirm(
        'You have removed all components. This will disable analysis watchlist. Continue anyway?'
      )
      if (!confirmed) return
    }

    onApprove(editableComponents)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-border rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-700">
          <h2 className="text-2xl font-bold text-dark-text mb-2">
            Review Analysis Components
          </h2>
          <p className="text-sm text-gray-400">
            {isGenerating
              ? 'AI is generating analysis criteria...'
              : components.length === 0
              ? 'Component generation failed. You can add custom components manually.'
              : `The AI generated ${components.length} watchlist ${
                  components.length === 1 ? 'criterion' : 'criteria'
                }. Review, edit, or add more before starting.`}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            Trigger threshold: <span className="font-semibold text-blue-400">{trigger_threshold}/10</span>
          </p>
        </div>

        {/* Component List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {editableComponents.length === 0 && !isAddingNew && (
            <div className="text-center py-12 text-gray-500">
              <p className="mb-4">No components configured.</p>
              <button
                onClick={() => setIsAddingNew(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition"
              >
                + Add Custom Component
              </button>
            </div>
          )}

          {editableComponents.map((comp, index) => (
            <div
              key={index}
              className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-3"
            >
              {/* Label */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Label (kebab-case identifier)
                </label>
                <input
                  type="text"
                  value={comp.label}
                  onChange={(e) => handleLabelChange(index, e.target.value)}
                  placeholder="e.g., committee-membership"
                  className="w-full bg-gray-800 text-dark-text border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Description (what to check for)
                </label>
                <textarea
                  value={comp.description}
                  onChange={(e) => handleDescriptionChange(index, e.target.value)}
                  placeholder="Describe what this component monitors..."
                  rows={2}
                  className="w-full bg-gray-800 text-dark-text border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm resize-y"
                />
              </div>

              {/* Remove Button */}
              <div className="flex justify-end">
                <button
                  onClick={() => handleRemove(index)}
                  className="text-red-400 hover:text-red-300 text-xs font-medium transition"
                >
                  ✕ Remove
                </button>
              </div>
            </div>
          ))}

          {/* Add New Component Form */}
          {isAddingNew && (
            <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-semibold text-blue-400">Add Custom Component</h3>

              {/* Label */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="e.g., geographic-accuracy"
                  className="w-full bg-gray-800 text-dark-text border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">
                  Description
                </label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="What should this component check for..."
                  rows={2}
                  className="w-full bg-gray-800 text-dark-text border border-gray-600 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm resize-y"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    setIsAddingNew(false)
                    setNewLabel('')
                    setNewDescription('')
                  }}
                  className="text-gray-400 hover:text-gray-300 text-sm font-medium transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddNew}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition"
                >
                  Add Component
                </button>
              </div>
            </div>
          )}

          {/* Add New Button (when not already adding) */}
          {!isAddingNew && editableComponents.length > 0 && (
            <button
              onClick={() => setIsAddingNew(true)}
              className="w-full border-2 border-dashed border-gray-600 hover:border-blue-500 text-gray-400 hover:text-blue-400 py-3 rounded-lg transition flex items-center justify-center gap-2 text-sm font-medium"
            >
              <span className="text-lg">+</span> Add Custom Component
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-700 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-semibold transition"
          >
            Cancel
          </button>
          <button
            onClick={handleApprove}
            disabled={isGenerating}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg font-semibold transition"
          >
            {isGenerating ? 'Generating...' : `✓ Start Run with ${editableComponents.length} ${editableComponents.length === 1 ? 'Component' : 'Components'}`}
          </button>
        </div>
      </div>
    </div>
  )
}
