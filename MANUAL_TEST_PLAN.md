# CNI Digital Queue Management System - Manual Test Plan

## 🎯 Overview
This comprehensive manual test plan allows you to validate all system optimizations from the browser. Follow these tests in order to verify that all phases of optimization are working correctly.

## 🚀 Pre-Test Setup

### 1. Install Dependencies (if not already done)
```bash
cd c:\Users\Gadaphy\Documents\Projects\CNI-Digital-Queue-Management-System\src
pip install -r requirements.txt
```

### 2. Create Admin User and Test Data (if not already done)
```bash
cd c:\Users\Gadaphy\Documents\Projects\CNI-Digital-Queue-Management-System
python create_admin_user.py
python create_test_data.py
```
This creates:
- **Admin**: ADMIN001 / admin123
- **Test Agents**: AGENT001, AGENT002, AGENT003 / agent123
- **Service Types**: New Application, Renewal, Collection, Correction, Emergency
- **Test Citizens**: 5 citizens with different profiles
- **Stations**: 3 test stations

### 3. Initialize Database (if needed)
If this is the first time running the application, you may need to initialize the database:
```bash
cd c:\Users\Gadaphy\Documents\Projects\CNI-Digital-Queue-Management-System\src
flask db upgrade
```

### 4. Start the Application
```bash
cd c:\Users\Gadaphy\Documents\Projects\CNI-Digital-Queue-Management-System\src
python run.py
```

**Expected Output**: You should see Flask development server starting, typically on `http://127.0.0.1:5000`

### 5. Open Multiple Browser Windows/Tabs
- **Tab 1**: Admin Dashboard - `http://localhost:5000/admin/dashboard`
- **Tab 2**: Agent Dashboard - `http://localhost:5000/agent/dashboard`
- **Tab 3**: Kiosk Interface - `http://localhost:5000/kiosk`
- **Tab 4**: Main Dashboard - `http://localhost:5000/dashboard` (Agent view)
- **Tab 5**: Browser Developer Tools (F12) - Monitor Network and Console

**Note**: There is no separate public display route in the current system. The main dashboard serves as the agent interface.

### 6. Create Test Data (Important!)
For meaningful testing, you'll need some basic data in the system. You can either:

**Option A**: Use the admin interface to create:
- At least 2-3 service types (e.g., "Document Collection", "New Application", "Emergency Service")
- At least 2-3 agents (besides the admin)
- A few test citizens with different profiles (normal, elderly, disabled, pregnant)

**Option B**: If available, run any data seeding scripts or use the test data creation functionality we built.

**Minimum Required Data for Testing**:
- ✅ At least 1 admin user (created by script)
- ✅ At least 2 agents for assignment testing
- ✅ At least 3 service types with different priority levels
- ✅ At least 5 test citizens with varied profiles
- ✅ A few test tickets in different statuses

---

## 📋 Phase 1: Admin Interface Functionality Tests

### Test 1.1: Admin Login and Dashboard Access
**Objective**: Verify admin interface is accessible and functional

**Steps**:
1. Navigate to `http://localhost:5000/auth/login` (main login page)
2. Login with admin credentials:
   - **Employee ID**: ADMIN001
   - **Password**: admin123
3. Navigate to `http://localhost:5000/admin/dashboard`
4. Verify dashboard loads without errors
5. Check that all menu items are accessible

**Note**: Make sure you ran both `create_admin_user.py` and `create_test_data.py` scripts first.

**Expected Results**:
- ✅ Dashboard loads quickly (< 2 seconds)
- ✅ No JavaScript errors in console
- ✅ All navigation links work
- ✅ Dashboard shows current queue statistics

**Pass/Fail**: ⬜

---

### Test 1.2: Queue Management Operations
**Objective**: Test core queue management functionality

**Steps**:
1. Go to Queue Management section
2. View current tickets in queue
3. Try to assign a ticket to an agent
4. Update ticket priority
5. Cancel a ticket
6. Call next ticket

**Expected Results**:
- ✅ Ticket list loads with proper pagination
- ✅ Ticket assignment works without errors
- ✅ Priority updates are saved and reflected immediately
- ✅ Ticket cancellation updates status correctly
- ✅ Call next ticket changes status to "in_progress"

**Pass/Fail**: ⬜

---

### Test 1.3: API Endpoints Testing
**Objective**: Verify all admin API endpoints work correctly

**Steps**:
1. Open Browser Developer Tools (F12)
2. Go to Network tab
3. Perform various admin actions (assign, cancel, update priority)
4. Check API responses in Network tab

**Expected Results**:
- ✅ All API calls return 200 status codes
- ✅ Response times are under 500ms
- ✅ JSON responses are properly formatted
- ✅ No 500 or 404 errors

**Pass/Fail**: ⬜

---

## 🧮 Phase 2: Simplified Queue Optimization Tests

### Test 2.1: Priority Calculation Consistency
**Objective**: Verify priority calculation works consistently

**Steps**:
1. Create tickets for different citizen types:
   - Normal citizen
   - Elderly citizen (65+ years old)
   - Citizen with disability
   - Pregnant citizen
2. Check priority scores assigned to each
3. Verify elderly/disabled/pregnant get higher priorities

**Expected Results**:
- ✅ Normal citizen gets base priority (e.g., 500-600)
- ✅ Elderly citizen gets bonus (+100 points)
- ✅ Disabled citizen gets higher bonus (+150 points)
- ✅ Pregnant citizen gets bonus (+120 points)
- ✅ Priority calculation is consistent across multiple tests

**Pass/Fail**: ⬜

---

### Test 2.2: Queue Optimization
**Objective**: Test the simplified queue optimization system

**Steps**:
1. Create 5-10 test tickets with different priorities
2. Go to Admin Dashboard
3. Click "Optimize Queue" button
4. Observe ticket reordering
5. Verify tickets are ordered by priority (highest first)

**Expected Results**:
- ✅ Optimization completes in under 2 seconds
- ✅ Tickets are reordered by priority score
- ✅ Success message is displayed
- ✅ No errors in console
- ✅ Real-time updates work across all tabs

**Pass/Fail**: ⬜

---

### Test 2.3: Agent Assignment Logic
**Objective**: Verify simplified agent assignment works

**Steps**:
1. Ensure multiple agents are available
2. Assign tickets to agents
3. Check agent workload distribution
4. Verify agents with fewer tickets get priority

**Expected Results**:
- ✅ Available agents are shown in assignment dropdown
- ✅ Agents with fewer active tickets are preferred
- ✅ Agent status updates to "busy" when assigned
- ✅ Assignment is immediate and reliable

**Pass/Fail**: ⬜

---

## ⚡ Phase 3: Database Performance Tests

### Test 3.1: Dashboard Loading Performance
**Objective**: Verify optimized database queries improve performance

**Steps**:
1. Clear browser cache
2. Open Developer Tools → Network tab
3. Refresh admin dashboard
4. Check loading times and number of requests
5. Repeat test 3 times and average the results

**Expected Results**:
- ✅ Dashboard loads in under 1 second
- ✅ Minimal number of API requests (< 5)
- ✅ No slow queries (all under 100ms)
- ✅ Consistent performance across multiple loads

**Performance Metrics**:
- Load Time: _____ ms
- API Requests: _____
- Slowest Query: _____ ms

**Pass/Fail**: ⬜

---

### Test 3.2: Pagination Performance
**Objective**: Test pagination with large datasets

**Steps**:
1. Go to ticket list with pagination
2. Navigate through multiple pages
3. Change page size (10, 25, 50 items)
4. Monitor loading times for each page

**Expected Results**:
- ✅ Page navigation is instant (< 200ms)
- ✅ Large page sizes (50 items) load quickly
- ✅ No performance degradation with page changes
- ✅ Smooth scrolling and interaction

**Pass/Fail**: ⬜

---

### Test 3.3: Search and Filter Performance
**Objective**: Verify search operations are optimized

**Steps**:
1. Use search functionality to find specific tickets
2. Apply various filters (status, service type, date)
3. Combine multiple filters
4. Monitor response times

**Expected Results**:
- ✅ Search results appear instantly (< 300ms)
- ✅ Filters work correctly and quickly
- ✅ Combined filters don't slow down system
- ✅ No database timeout errors

**Pass/Fail**: ⬜

---

## 🔄 Phase 4: WebSocket Synchronization Tests

### Test 4.1: Real-time Updates Across Tabs
**Objective**: Verify WebSocket synchronization works correctly

**Steps**:
1. Open Admin Dashboard in Tab 1
2. Open Agent Dashboard in Tab 2
3. Open Public Display in Tab 3
4. In Tab 1, assign a ticket to an agent
5. Check if updates appear in Tabs 2 and 3 immediately

**Expected Results**:
- ✅ Updates appear in all tabs within 1 second
- ✅ Data is consistent across all interfaces
- ✅ No duplicate or missing updates
- ✅ WebSocket connection is stable

**Pass/Fail**: ⬜

---

### Test 4.2: Concurrent Operations Test
**Objective**: Test system behavior with simultaneous operations

**Steps**:
1. Open 2 admin tabs side by side
2. Simultaneously try to:
   - Assign the same ticket to different agents
   - Update priority of the same ticket
   - Cancel and call the same ticket
3. Observe conflict resolution

**Expected Results**:
- ✅ Only one operation succeeds (no conflicts)
- ✅ Error messages are clear and helpful
- ✅ Data remains consistent
- ✅ No system crashes or freezes

**Pass/Fail**: ⬜

---

### Test 4.3: Connection Recovery Test
**Objective**: Test WebSocket reconnection handling

**Steps**:
1. Open admin dashboard
2. Disconnect internet/network briefly (10 seconds)
3. Reconnect network
4. Perform queue operations
5. Check if missed updates are synchronized

**Expected Results**:
- ✅ System detects disconnection
- ✅ Automatic reconnection occurs
- ✅ Missed updates are synchronized
- ✅ No data loss or inconsistencies

**Pass/Fail**: ⬜

---

## 🔄 Integration Tests

### Test 5.1: Complete Ticket Lifecycle
**Objective**: Test entire ticket journey from creation to completion

**Steps**:
1. **Kiosk Tab**: Navigate to `http://localhost:5000/kiosk` and create a new ticket
2. **Admin Tab**: Go to `http://localhost:5000/admin/dashboard` and verify ticket appears in queue
3. **Admin Tab**: Use the "Optimize Queue" functionality
4. **Admin Tab**: Assign ticket to an available agent
5. **Agent Tab**: Go to `http://localhost:5000/agent/dashboard` and manage the assigned ticket
6. **Agent Tab**: Complete the ticket service
7. **All Tabs**: Verify real-time updates appear across all interfaces

**Expected Results**:
- ✅ Ticket creation is immediate
- ✅ Queue optimization works correctly
- ✅ Assignment is successful
- ✅ Agent can manage ticket
- ✅ Completion updates all interfaces
- ✅ All steps complete without errors

**Pass/Fail**: ⬜

---

### Test 5.2: High Load Simulation
**Objective**: Test system performance under load

**Steps**:
1. Create 20+ test tickets quickly
2. Perform multiple simultaneous operations:
   - Optimize queue
   - Assign multiple tickets
   - Update priorities
   - Cancel some tickets
3. Monitor system responsiveness

**Expected Results**:
- ✅ System remains responsive
- ✅ All operations complete successfully
- ✅ No timeouts or errors
- ✅ Real-time updates continue working

**Pass/Fail**: ⬜

---

### Test 5.3: Error Handling and Recovery
**Objective**: Verify system handles errors gracefully

**Steps**:
1. Try invalid operations:
   - Assign ticket to non-existent agent
   - Update with invalid priority values
   - Cancel already completed ticket
2. Check error messages and system recovery

**Expected Results**:
- ✅ Clear, helpful error messages
- ✅ System doesn't crash
- ✅ User can continue working after errors
- ✅ Data integrity is maintained

**Pass/Fail**: ⬜

---

## 📊 Performance Benchmarks

### Load Time Targets
- **Dashboard Load**: < 1 second
- **Queue Optimization**: < 2 seconds
- **Ticket Assignment**: < 500ms
- **Real-time Updates**: < 1 second
- **Search/Filter**: < 300ms

### Reliability Targets
- **WebSocket Uptime**: > 99%
- **API Success Rate**: > 99%
- **Data Consistency**: 100%
- **Error Recovery**: < 5 seconds

---

## 🎯 Test Results Summary

### Phase 1: Admin Interface
- Test 1.1 - Dashboard Access: ⬜ Pass / ⬜ Fail
- Test 1.2 - Queue Management: ⬜ Pass / ⬜ Fail
- Test 1.3 - API Endpoints: ⬜ Pass / ⬜ Fail

### Phase 2: Queue Optimization
- Test 2.1 - Priority Calculation: ⬜ Pass / ⬜ Fail
- Test 2.2 - Queue Optimization: ⬜ Pass / ⬜ Fail
- Test 2.3 - Agent Assignment: ⬜ Pass / ⬜ Fail

### Phase 3: Database Performance
- Test 3.1 - Dashboard Performance: ⬜ Pass / ⬜ Fail
- Test 3.2 - Pagination Performance: ⬜ Pass / ⬜ Fail
- Test 3.3 - Search Performance: ⬜ Pass / ⬜ Fail

### Phase 4: WebSocket Synchronization
- Test 4.1 - Real-time Updates: ⬜ Pass / ⬜ Fail
- Test 4.2 - Concurrent Operations: ⬜ Pass / ⬜ Fail
- Test 4.3 - Connection Recovery: ⬜ Pass / ⬜ Fail

### Integration Tests
- Test 5.1 - Complete Lifecycle: ⬜ Pass / ⬜ Fail
- Test 5.2 - High Load: ⬜ Pass / ⬜ Fail
- Test 5.3 - Error Handling: ⬜ Pass / ⬜ Fail

---

## 📝 Notes and Issues Found

**Issues Discovered**:
1. _________________________________
2. _________________________________
3. _________________________________

**Performance Notes**:
1. _________________________________
2. _________________________________
3. _________________________________

**Recommendations**:
1. _________________________________
2. _________________________________
3. _________________________________

---

## ✅ Final Assessment

**Overall System Status**: ⬜ Production Ready / ⬜ Needs Minor Fixes / ⬜ Needs Major Work

**Test Completion Date**: _______________

**Tester**: _______________

**Total Tests Passed**: _____ / 15

**Success Rate**: _____%

---

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

**Issue**: Dashboard won't load
- **Solution**: Check if Flask app is running with `python run.py`, verify port 5000 is available

**Issue**: Authentication errors
- **Solution**: You may need to create admin/agent users first. Check if there's a user creation endpoint or seed data

**Issue**: WebSocket updates not working
- **Solution**: Check browser console for WebSocket errors, refresh page. The app uses SocketIO for real-time updates

**Issue**: API calls failing
- **Solution**: Check network tab for error details, verify database connection. Database is SQLite by default

**Issue**: Slow performance
- **Solution**: Check that database indexes are created, monitor system resources

**Issue**: Priority calculation seems wrong
- **Solution**: Verify citizen data (age, special needs) is correct. The system now uses simplified priority calculation

**Issue**: Routes not found (404 errors)
- **Solution**: 
  - Admin routes are under `/admin/` prefix (e.g., `/admin/dashboard`)
  - Agent routes are under `/agent/` prefix (e.g., `/agent/dashboard`) 
  - Kiosk routes are under `/kiosk/` prefix
  - Main dashboard is at `/dashboard`
  - Authentication is at `/auth/login`

**Issue**: Database not initialized
- **Solution**: You may need to run database migrations or initialization scripts first

---

## 📞 Support

If you encounter issues during testing:
1. Check browser console for JavaScript errors
2. Check Flask application logs
3. Verify database connection and data
4. Test with different browsers
5. Clear browser cache and cookies

## 📝 Test Plan Corrections Made

Based on the actual codebase analysis, the following corrections were made to ensure accuracy:

### ✅ **Corrected Issues**:
1. **Startup Command**: Changed from `python app.py` to `python run.py`
2. **Route URLs**: Updated to reflect actual URL structure:
   - Admin: `/admin/dashboard` (not `/admin`)
   - Agent: `/agent/dashboard` (not `/agent`)
   - Authentication: `/auth/login`
3. **Admin Credentials**: Provided actual credentials from `create_admin_user.py`
4. **Database Setup**: Added database initialization steps (`flask db upgrade`)
5. **Dependencies**: Added installation of requirements.txt
6. **Public Display**: Removed non-existent public display route
7. **Kiosk Route Fix**: Fixed duplicate blueprint definition causing 404 on `/kiosk`
8. **Test Data Requirements**: Added section about creating necessary test data
9. **Troubleshooting**: Enhanced with actual system architecture details

### ✅ **System Architecture Confirmed**:
- Flask application with SocketIO for real-time updates
- SQLite database (configurable to PostgreSQL)
- Blueprint-based route organization
- Flask-Login for authentication
- Flask-Migrate for database migrations
- Encrypted citizen data storage

### ✅ **Authentication System**:
- Admin user creation script available
- Email/password based login
- Role-based access control
- JWT tokens for API authentication

**Remember**: This corrected test plan now accurately reflects the actual system implementation and validates all the optimizations we implemented across all 4 phases. Take your time with each test and document any issues you find!
