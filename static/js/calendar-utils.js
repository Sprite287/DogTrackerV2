/**
 * Calendar Utilities - Shared functions for calendar functionality
 */

// Event category mapping based on event type and properties
const EVENT_CATEGORIES = {
    vet: {
        color: '#e74c3c',
        keywords: ['vet', 'medical', 'surgery', 'treatment', 'emergency']
    },
    checkup: {
        color: '#2ecc71',
        keywords: ['checkup', 'wellness', 'routine', 'physical']
    },
    grooming: {
        color: '#3498db',
        keywords: ['groom', 'grooming', 'bath', 'nail']
    },
    medication: {
        color: '#f39c12',
        keywords: ['medicine', 'medication', 'dose']
    },
    other: {
        color: '#95a5a6',
        keywords: []
    }
};

/**
 * Determine event category based on event properties
 * @param {Object} event - Event object with extendedProps
 * @returns {Object} Category object with name and color
 */
function getEventCategory(event) {
    // Check for medication events
    if (event.extendedProps?.eventType === 'medicine_start' || 
        event.extendedProps?.eventType === 'medicine_end') {
        return { name: 'medication', color: EVENT_CATEGORIES.medication.color };
    }
    
    // Check for appointment events
    if (event.extendedProps?.eventType === 'appointment') {
        const appointmentType = (event.extendedProps.appointment_type || '').toLowerCase();
        
        // Check each category's keywords
        for (const [categoryName, categoryData] of Object.entries(EVENT_CATEGORIES)) {
            if (categoryData.keywords.some(keyword => appointmentType.includes(keyword))) {
                return { name: categoryName, color: categoryData.color };
            }
        }
    }
    
    // Default to 'other' category
    return { name: 'other', color: EVENT_CATEGORIES.other.color };
}

/**
 * Transform raw event data to FullCalendar format
 * @param {Object} event - Raw event from API
 * @returns {Object} Transformed event for FullCalendar
 */
function transformCalendarEvent(event) {
    const category = getEventCategory(event);
    
    return {
        id: event.id,
        title: event.title,
        start: event.start,
        end: event.end,
        allDay: event.allDay || false,
        backgroundColor: category.color,
        borderColor: category.color,
        textColor: 'white',
        extendedProps: {
            category: category.name,
            dog_name: event.extendedProps?.dog_name,
            dog_id: event.extendedProps?.dog_id,
            location: event.extendedProps?.location,
            notes: event.extendedProps?.notes || event.extendedProps?.description,
            vet_name: event.extendedProps?.vet_name,
            appointment_type: event.extendedProps?.appointment_type,
            medicine_name: event.extendedProps?.medicine_name,
            eventType: event.extendedProps?.eventType
        }
    };
}

/**
 * Build tooltip content for calendar events
 * @param {Object} event - FullCalendar event object
 * @returns {string} HTML content for tooltip
 */
function buildEventTooltip(event) {
    let content = '<div class="calendar-tooltip">';
    content += `<strong>${event.title}</strong><br>`;
    
    if (event.extendedProps.dog_name) {
        content += `<i class="bi bi-heart-fill"></i> ${event.extendedProps.dog_name}<br>`;
    }
    
    const timeStr = formatEventTime(event);
    content += `<i class="bi bi-clock"></i> ${timeStr}<br>`;
    
    if (event.extendedProps.location) {
        content += `<i class="bi bi-geo-alt"></i> ${event.extendedProps.location}<br>`;
    }
    
    if (event.extendedProps.vet_name) {
        content += `<i class="bi bi-person"></i> Dr. ${event.extendedProps.vet_name}<br>`;
    }
    
    if (event.extendedProps.notes) {
        content += `<small>${event.extendedProps.notes}</small>`;
    }
    
    content += '</div>';
    return content;
}

/**
 * Format event time for display
 * @param {Object} event - FullCalendar event object
 * @returns {string} Formatted time string
 */
function formatEventTime(event) {
    if (event.allDay) {
        return 'All day';
    }
    
    return event.start.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
}

/**
 * Format date for display
 * @param {Date} date - Date object
 * @param {Object} options - Formatting options
 * @returns {string} Formatted date string
 */
function formatDate(date, options = {}) {
    const defaultOptions = {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    };
    
    return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
}

/**
 * Build calendar event fetch parameters
 * @param {Date} start - Start date
 * @param {Date} end - End date
 * @param {Object} filters - Additional filters (rescue_id, etc.)
 * @returns {URLSearchParams} URL parameters for API request
 */
function buildEventFetchParams(start, end, filters = {}) {
    const params = new URLSearchParams({
        start: start.toISOString(),
        end: end.toISOString()
    });
    
    // Add rescue filter if present
    const rescueSelect = document.getElementById('rescueSelect');
    if (rescueSelect && rescueSelect.value) {
        params.append('rescue_id', rescueSelect.value);
    }
    
    // Check URL parameters for rescue_id
    const urlParams = new URLSearchParams(window.location.search);
    const urlRescueId = urlParams.get('rescue_id');
    if (urlRescueId && !params.has('rescue_id')) {
        params.append('rescue_id', urlRescueId);
    }
    
    // Add any additional filters
    Object.entries(filters).forEach(([key, value]) => {
        if (value && !params.has(key)) {
            params.append(key, value);
        }
    });
    
    return params;
}

/**
 * Clean up modal backdrops and state
 * Useful for fixing Bootstrap modal issues
 */
function cleanupModals() {
    // Remove any remaining modal backdrops
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
    
    // Ensure body doesn't have modal-open class
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
}

/**
 * Initialize Bootstrap tooltips on elements
 * @param {HTMLElement} container - Container to search for tooltip elements
 */
function initializeTooltips(container = document) {
    const tooltipElements = container.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipElements.forEach(el => {
        // Dispose of existing tooltip if any
        const existingTooltip = bootstrap.Tooltip.getInstance(el);
        if (existingTooltip) {
            existingTooltip.dispose();
        }
        // Create new tooltip
        new bootstrap.Tooltip(el);
    });
}

/**
 * Handle scroll to element with smooth behavior
 * @param {HTMLElement} element - Element to scroll to
 * @param {Object} options - Scroll options
 */
function smoothScrollToElement(element, options = {}) {
    const defaultOptions = {
        behavior: 'smooth',
        block: 'nearest',
        inline: 'nearest'
    };
    
    if (element) {
        element.scrollIntoView({ ...defaultOptions, ...options });
    }
}

/**
 * Update show more/less button state and text
 * @param {HTMLElement} btn - Button element
 * @param {number} currentCount - Current visible items
 * @param {number} totalCount - Total items available
 * @param {boolean} isExpanded - Whether list is expanded
 * @returns {void}
 */
function updateShowMoreButton(btn, currentCount, totalCount, isExpanded = false) {
    const remainingCount = totalCount - currentCount;
    const incrementSize = 5;
    
    if (isExpanded || remainingCount <= 0) {
        if (currentCount > incrementSize) {
            btn.innerHTML = '<i class="bi bi-chevron-up"></i> Show less';
            btn.classList.add('expanded');
            btn.classList.remove('d-none');
        } else {
            btn.classList.add('d-none');
        }
    } else {
        const nextIncrement = Math.min(incrementSize, remainingCount);
        btn.innerHTML = `<i class="bi bi-chevron-down"></i> Show ${nextIncrement} more`;
        btn.classList.remove('expanded');
        btn.classList.remove('d-none');
    }
}

/**
 * Remove event listeners and re-attach to prevent duplicates
 * @param {HTMLElement} element - Element to clean
 * @returns {HTMLElement} Cloned element without listeners
 */
function removeEventListeners(element) {
    const clone = element.cloneNode(true);
    element.replaceWith(clone);
    return clone;
}

/**
 * Build URL with query parameters
 * @param {string} baseUrl - Base URL
 * @param {URLSearchParams|Object} params - Parameters to add
 * @returns {string} Complete URL with parameters
 */
function buildUrlWithParams(baseUrl, params) {
    const searchParams = params instanceof URLSearchParams 
        ? params 
        : new URLSearchParams(params);
    
    const paramString = searchParams.toString();
    return paramString ? `${baseUrl}?${paramString}` : baseUrl;
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        EVENT_CATEGORIES,
        getEventCategory,
        transformCalendarEvent,
        buildEventTooltip,
        formatEventTime,
        formatDate,
        buildEventFetchParams,
        cleanupModals,
        initializeTooltips,
        smoothScrollToElement,
        updateShowMoreButton,
        removeEventListeners,
        buildUrlWithParams
    };
}