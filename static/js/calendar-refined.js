// Calendar Page - Complete Refinement
// ===================================
// Proper FullCalendar 6.1.11 integration with all views working

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Calendar Refined] Initializing FullCalendar properly...');
    
    // Initialize FullCalendar
    initializeFullCalendar();
    
    // Initialize view switcher
    initializeViewSwitcher();
    
    // Initialize reminder tabs
    initializeReminderTabs();
    
    // Initialize reminder actions
    initializeReminderActions();
    
    // Initialize show more functionality
    initializeShowMore();
    
    // Update today's date
    updateTodayDate();
});

// Global calendar instance
let calendar = null;

// Initialize FullCalendar with proper configuration
function initializeFullCalendar() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) {
        console.error('Calendar element not found');
        return;
    }
    
    // Show loading state
    calendarEl.innerHTML = '<div class="calendar-loading"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    // Create calendar instance
    calendar = new FullCalendar.Calendar(calendarEl, {
        // Core settings
        initialView: 'dayGridMonth',
        headerToolbar: false, // We use custom header
        height: 'auto',
        fixedWeekCount: false, // Show only weeks of current month
        showNonCurrentDates: false, // Hide dates from other months
        
        // Event settings - better handling for overlapping events
        dayMaxEvents: 4, // Show up to 4 events, then "+X more"
        eventDisplay: 'block',
        eventOrder: 'start,-duration,title', // Smart ordering
        eventTimeFormat: {
            hour: 'numeric',
            minute: '2-digit',
            meridiem: 'short'
        },
        
        // Core time settings for all views
        slotMinTime: '06:00:00',
        slotMaxTime: '22:00:00',
        slotDuration: '00:30:00',
        nowIndicator: true,
        allDaySlot: true,
        
        // Views configuration
        views: {
            dayGridMonth: {
                dayMaxEvents: 4, // Consistent with main setting
                moreLinkClick: 'popover'
            },
            timeGridWeek: {
                titleFormat: { year: 'numeric', month: 'short', day: 'numeric' },
                dayHeaderFormat: { weekday: 'short', month: 'numeric', day: 'numeric' }
            },
            timeGridDay: {
                titleFormat: { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }
            },
            listWeek: {
                listDayFormat: { weekday: 'long', month: 'long', day: 'numeric' }
            }
        },
        
        // Event source - fetch from API
        events: function(info, successCallback, failureCallback) {
            console.log('[Calendar] FullCalendar requesting events for:', info.start, 'to', info.end);
            fetchCalendarEvents(info.start, info.end)
                .then(events => {
                    console.log('[Calendar] Calling successCallback with', events.length, 'events');
                    successCallback(events);
                })
                .catch(error => {
                    console.error('[Calendar] Error in event source:', error);
                    failureCallback(error);
                });
        },
        
        // Event rendering
        eventDidMount: function(info) {
            console.log('[Calendar] Rendering event:', info.event.title, info.event);
            
            // Add category class for styling
            const category = info.event.extendedProps.category || 'other';
            info.el.classList.add(category);
            
            // Initialize Bootstrap tooltip
            const tooltipContent = buildTooltipContent(info.event);
            info.el.setAttribute('data-bs-toggle', 'tooltip');
            info.el.setAttribute('data-bs-placement', 'top');
            info.el.setAttribute('data-bs-html', 'true');
            info.el.setAttribute('title', tooltipContent);
            
            // Initialize tooltip using utility function
            initializeTooltips(info.el.parentElement);
        },
        
        // Event click - navigate to dog profile
        eventClick: function(info) {
            // Navigate to dog profile if available
            if (info.event.extendedProps.dog_id) {
                window.location.href = `/dogs/${info.event.extendedProps.dog_id}`;
            } else if (info.event.url && info.event.url !== '#') {
                window.location.href = info.event.url;
            }
        },
        
        // More link click
        moreLinkClick: 'popover',
        moreLinkContent: function(arg) {
            return '+' + arg.num + ' more';
        }
    });
    
    // Render calendar
    calendar.render();
    
    // Initialize month navigation after a short delay to ensure calendar is ready
    setTimeout(() => {
        initializeMonthNavigation();
    }, 100);
}

// Fetch calendar events from API
async function fetchCalendarEvents(start, end) {
    try {
        console.log('[Calendar] Fetching events for range:', start.toISOString(), 'to', end.toISOString());
        
        // Build URL parameters using utility function
        const params = buildEventFetchParams(start, end);
        
        console.log('[Calendar] API URL:', `/api/calendar/events?${params}`);
        const response = await fetch(`/api/calendar/events?${params}`);
        console.log('[Calendar] Response status:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[Calendar] API Error:', response.status, errorText);
            throw new Error(`Failed to fetch events: ${response.status} ${errorText}`);
        }
        
        const events = await response.json();
        console.log('[Calendar] Raw events from API:', events);
        
        // Transform events using utility function
        const transformedEvents = events.map(transformCalendarEvent);
        
        console.log('[Calendar] Transformed events:', transformedEvents);
        return transformedEvents;
        
    } catch (error) {
        console.error('Error fetching calendar events:', error);
        showAlert('Failed to load calendar events. Please refresh the page.', 'warning');
        return [];
    }
}

// Build tooltip content - delegate to utility function
function buildTooltipContent(event) {
    return buildEventTooltip(event);
}

// Initialize view switcher
function initializeViewSwitcher() {
    const viewButtons = document.querySelectorAll('.view-btn');
    
    viewButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Update active state
            viewButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Get view name from button text
            const viewName = this.textContent.trim().toLowerCase();
            
            // Change calendar view
            if (calendar) {
                switch(viewName) {
                    case 'month':
                        calendar.changeView('dayGridMonth');
                        break;
                    case 'week':
                        calendar.changeView('timeGridWeek');
                        break;
                    case 'day':
                        calendar.changeView('timeGridDay');
                        break;
                    case 'list':
                        calendar.changeView('listWeek');
                        break;
                }
            }
        });
    });
}

// Initialize reminder tabs
function initializeReminderTabs() {
    const tabs = document.querySelectorAll('.reminder-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Update active content
            const tabName = this.dataset.tab;
            document.querySelectorAll('.reminder-tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            const activeContent = document.getElementById(`${tabName}-content`);
            if (activeContent) {
                activeContent.classList.add('active');
            }
        });
    });
}

// Initialize reminder actions
function initializeReminderActions() {
    // Delegate click events for reminder buttons
    document.addEventListener('click', function(e) {
        if (e.target.closest('.btn-complete')) {
            e.preventDefault();
            const btn = e.target.closest('.btn-complete');
            const reminderItem = btn.closest('.reminder-item');
            const reminderId = reminderItem.dataset.reminderId;
            
            if (reminderId) {
                completeReminder(reminderId, reminderItem);
            }
        }
    });
}

// Complete reminder
async function completeReminder(reminderId, itemElement) {
    const btn = itemElement.querySelector('.btn-complete');
    const originalContent = btn.innerHTML;
    
    // Show loading state
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
    btn.disabled = true;
    
    try {
        // Get CSRF token using core utility
        const csrfToken = getCsrfToken();
        
        const response = await fetch(`/calendar/acknowledge_reminder/${reminderId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            }
        });
        
        if (response.ok) {
            // Animate and remove using CSS classes instead of inline styles
            itemElement.classList.add('reminder-removing');
            
            setTimeout(() => {
                itemElement.remove();
                updateReminderCounts();
                
                // Check if tab is empty
                checkEmptyTabs();
            }, 300);
        } else {
            throw new Error('Failed to complete reminder');
        }
        
    } catch (error) {
        console.error('Error completing reminder:', error);
        showAlert('Failed to complete reminder. Please try again.', 'warning');
        // Restore button
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

// Update reminder counts
function updateReminderCounts() {
    let totalCount = 0;
    
    // Update each tab count
    document.querySelectorAll('.reminder-tab').forEach(tab => {
        const tabName = tab.dataset.tab;
        const content = document.getElementById(`${tabName}-content`);
        if (content) {
            const count = content.querySelectorAll('.reminder-item').length;
            const countBadge = tab.querySelector('.tab-count');
            if (countBadge) {
                countBadge.textContent = count;
            }
            totalCount += count;
        }
    });
    
    // Update total count
    const totalBadge = document.querySelector('.reminder-count');
    if (totalBadge) {
        totalBadge.textContent = totalCount;
    }
}

// Check for empty tabs
function checkEmptyTabs() {
    document.querySelectorAll('.reminder-tab-content').forEach(content => {
        const items = content.querySelectorAll('.reminder-item');
        if (items.length === 0 && !content.querySelector('.empty-reminders')) {
            // Add empty state
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-reminders';
            emptyState.innerHTML = `
                <i class="bi bi-check-circle"></i>
                <p>No reminders in this category</p>
            `;
            content.appendChild(emptyState);
        }
    });
}

// Update today's date
function updateTodayDate() {
    const todayEl = document.querySelector('.today-date');
    if (todayEl) {
        const today = new Date();
        const dateStr = formatDate(today);
        todayEl.textContent = dateStr;
    }
}

// Handle calendar navigation
document.addEventListener('keydown', function(e) {
    if (!calendar) return;
    
    // Arrow keys for navigation
    if (e.key === 'ArrowLeft' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        calendar.prev();
    } else if (e.key === 'ArrowRight' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        calendar.next();
    } else if (e.key === 't' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        calendar.today();
    }
});

// Handle add event button
document.addEventListener('click', function(e) {
    if (e.target.closest('.btn-add-event')) {
        e.preventDefault();
        const modal = document.getElementById('addAppointmentModal');
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    }
});

// Initialize show more functionality
function initializeShowMore() {
    document.addEventListener('click', function(e) {
        if (e.target.closest('.show-more-btn')) {
            e.preventDefault();
            const btn = e.target.closest('.show-more-btn');
            const category = btn?.dataset?.category;
            
            if (btn && category) {
                console.log('[Show More] Button clicked, expanded:', btn.classList.contains('expanded'));
                if (btn.classList.contains('expanded')) {
                    // Collapse - show only first 5
                    showLessReminders(category, btn);
                } else {
                    // Expand - show all
                    showMoreReminders(category, btn);
                }
            }
        }
    });
}

// Show more reminders
function showMoreReminders(category, btn) {
    const content = document.getElementById(`${category}-content`);
    const currentItems = content.querySelectorAll('.reminder-item');
    const currentCount = currentItems.length;
    const totalCount = parseInt(btn.dataset.total) || 0;
    const incrementSize = 5; // Show 5 more items each time
    
    // Calculate how many more to show
    const remainingCount = totalCount - currentCount;
    const itemsToShow = Math.min(incrementSize, remainingCount);
    
    if (itemsToShow <= 0) {
        btn.classList.add('d-none');
        return;
    }
    
    const loadingHtml = '<span class="spinner-border spinner-border-sm" role="status"></span> Loading...';
    btn.innerHTML = loadingHtml;
    
    // Get rescue_id if present
    const urlParams = new URLSearchParams(window.location.search);
    const rescueId = urlParams.get('rescue_id');
    
    const params = new URLSearchParams();
    if (rescueId) {
        params.append('rescue_id', rescueId);
    }
    params.append('offset', currentCount.toString());
    params.append('limit', itemsToShow.toString());
    
    const url = buildUrlWithParams(`/calendar/reminders/${category}`, params);
    
    fetch(url, {
        headers: {
            'HX-Request': 'true'
        }
    })
    .then(response => response.text())
    .then(html => {
        const remindersHtml = html.trim();
        
        if (remindersHtml) {
            // Create temporary container to parse new items
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = remindersHtml;
            
            // Find the show more button in content and remove it temporarily
            const existingShowMoreBtn = content.querySelector('.show-more-btn');
            if (existingShowMoreBtn) {
                existingShowMoreBtn.remove();
            }
            
            // Append new reminder items (excluding any show-more button from response)
            const newItems = tempDiv.querySelectorAll('.reminder-item');
            newItems.forEach(item => {
                // Make sure new items are visible
                item.classList.remove('hidden-reminder');
                content.appendChild(item);
            });
            
            // Re-add the show more button
            content.appendChild(btn);
            
            // Scroll to show the newly added items
            setTimeout(() => {
                const lastNewItem = newItems[newItems.length - 1];
                smoothScrollToElement(lastNewItem);
            }, 100);
            
            // Update button text and state
            const newTotalShown = content.querySelectorAll('.reminder-item').length;
            const allShown = newTotalShown >= totalCount;
            updateShowMoreButton(btn, newTotalShown, totalCount, allShown);
        } else {
            // No more items available
            btn.classList.add('d-none');
        }
    })
    .catch(error => {
        console.error('Error loading more reminders:', error);
        showAlert('Failed to load more reminders. Please try again.', 'warning');
        btn.innerHTML = '<i class="bi bi-chevron-down"></i> Show more';
    });
}

// Show less reminders
function showLessReminders(category, btn) {
    const content = document.getElementById(`${category}-content`);
    const reminderItems = content.querySelectorAll('.reminder-item');
    
    // Remove dynamically loaded items (keep only the first 5 which were server-rendered)
    reminderItems.forEach((item, index) => {
        if (index >= 5) {
            // Remove dynamically loaded items completely
            item.remove();
        }
    });
    
    // Update button state
    const totalCount = parseInt(btn.dataset.total) || 0;
    const currentVisible = 5; // Now showing first 5
    updateShowMoreButton(btn, currentVisible, totalCount, false);
    
    // Scroll back to top of reminder section
    const firstVisibleItem = content.querySelector('.reminder-item');
    smoothScrollToElement(firstVisibleItem, { block: 'start' });
}

// Initialize month navigation
function initializeMonthNavigation() {
    const prevBtn = document.getElementById('prevMonth');
    const nextBtn = document.getElementById('nextMonth');
    const currentMonthEl = document.getElementById('currentMonthYear');
    
    if (prevBtn && nextBtn && currentMonthEl && calendar) {
        // Update the month display initially
        updateCurrentMonthDisplay();
        
        // Remove any existing listeners to prevent duplicates
        const newPrevBtn = removeEventListeners(prevBtn);
        const newNextBtn = removeEventListeners(nextBtn);
        
        // Previous month button
        newPrevBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (calendar) {
                calendar.prev();
                // Update will happen via datesSet event
            }
        });
        
        // Next month button
        newNextBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (calendar) {
                calendar.next();
                // Update will happen via datesSet event
            }
        });
        
        // Update month display when calendar view changes
        calendar.on('datesSet', function(info) {
            updateCurrentMonthDisplay();
        });
    }
}

// Update current month display
function updateCurrentMonthDisplay() {
    const currentMonthEl = document.getElementById('currentMonthYear');
    if (currentMonthEl && calendar) {
        const currentDate = calendar.getDate();
        const monthYear = formatDate(currentDate, {
            month: 'long',
            year: 'numeric'
        });
        currentMonthEl.textContent = monthYear;
    }
}

// Handle rescue filter changes
document.addEventListener('change', function(e) {
    if (e.target.id === 'rescueSelect' && calendar) {
        // Refetch events when rescue filter changes
        calendar.refetchEvents();
    }
});

// Fix modal backdrop issue
document.addEventListener('hidden.bs.modal', function (event) {
    cleanupModals();
});