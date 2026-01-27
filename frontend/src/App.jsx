import { useState, useEffect } from 'react'
import './App.css'

const API_URL = import.meta.env.PROD 
  ? 'https://api.denvertts303.com' 
  : 'http://localhost:8000'

const TIMES = [
  { label: "6:00 AM", minutes: 360 },
  { label: "7:00 AM", minutes: 420 },
  { label: "8:00 AM", minutes: 480 },
  { label: "9:00 AM", minutes: 540 },
  { label: "10:00 AM", minutes: 600 },
  { label: "11:00 AM", minutes: 660 },
  { label: "12:00 PM", minutes: 720 },
  { label: "1:00 PM", minutes: 780 },
  { label: "2:00 PM", minutes: 840 },
  { label: "3:00 PM", minutes: 900 },
  { label: "4:00 PM", minutes: 960 },
  { label: "5:00 PM", minutes: 1020 },
]

function App() {
  const [courses, setCourses] = useState([])
  const [teeTimes, setTeeTimes] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCourse, setSelectedCourse] = useState(null)
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  
  const [showAlertForm, setShowAlertForm] = useState(false)
  const [alertPhone, setAlertPhone] = useState('')
  const [alertTimeStart, setAlertTimeStart] = useState(420)
  const [alertTimeEnd, setAlertTimeEnd] = useState(600)
  const [alertMinSpots, setAlertMinSpots] = useState(1)
  const [alertStatus, setAlertStatus] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  const createAlert = async () => {
    const digits = alertPhone.replace(/\D/g, '')
    if (digits.length !== 10 && digits.length !== 11) {
      setAlertStatus('Please enter a valid 10-digit phone number')
      return
    }
    try {
      const res = await fetch(`${API_URL}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: alertPhone.startsWith('+') ? alertPhone : `+1${alertPhone.replace(/\D/g, '')}`,
          club_id: selectedCourse.club_id || 0,
          course_name: selectedCourse.name,
          date: date,
          time_start: alertTimeStart,
          time_end: alertTimeEnd,
          min_spots: alertMinSpots
        })
      })
      if (res.ok) {
        setAlertStatus('✓ Alert created! You\'ll get a text when times open up.')
        setTimeout(() => {
          setShowAlertForm(false)
          setAlertStatus('')
        }, 3000)
      } else {
        const err = await res.json()
        setAlertStatus(err.detail || 'Error creating alert')
      }
    } catch {
      setAlertStatus('Error creating alert')
    }
  }

  const openBooking = () => {
    if (selectedCourse.provider === 'chronogolf') {
      window.open(
        `https://www.chronogolf.com/club/south-suburban-golf-club?date=${date}`,
        '_blank'
      )
    } else {
      window.open(
        `https://app.membersports.com/tee-times/${selectedCourse.club_id}/${selectedCourse.course_id}/0/1/0`,
        '_blank'
      )
    }
  }

  useEffect(() => {
    fetch(`${API_URL}/api/courses`).then(r => r.json()).then(data => {
      setCourses(data)
      setSelectedCourse(data[3]) // Kennedy as default
    })
  }, [])

  useEffect(() => {
    if (!selectedCourse) return
    const fetchTimes = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_URL}/api/tee-times/${encodeURIComponent(selectedCourse.name)}/${date}`)
        setTeeTimes(await res.json())
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchTimes()
  }, [selectedCourse, date, refreshKey])

  return (
    <div className="app">
      <h1>⛳ Denver Golf Tee Times</h1>
      
      <div className="controls">
        <select 
          value={selectedCourse?.name || ''} 
          onChange={(e) => setSelectedCourse(courses.find(c => c.name === e.target.value))}
        >
          {courses.map(c => (
            <option key={c.name} value={c.name}>{c.name}</option>
          ))}
        </select>
        
        <input 
          type="date" 
          value={date} 
          onChange={(e) => setDate(e.target.value)} 
        />
        
        <button onClick={() => setRefreshKey(k => k + 1)}>Refresh</button>
      </div>

      <button 
        className="alert-toggle"
        onClick={() => setShowAlertForm(!showAlertForm)}
      >
        🔔 {showAlertForm ? 'Hide Alert Form' : 'Set Up Alert'}
      </button>

      {showAlertForm && (
        <div className="alert-form">
          <p>Get a text when tee times at <strong>{selectedCourse?.name}</strong> on <strong>{date}</strong> become available:</p>
          <div className="alert-fields">
            <input
              type="tel"
              placeholder="Phone number"
              value={alertPhone}
              onChange={(e) => setAlertPhone(e.target.value)}
            />
            <select value={alertTimeStart} onChange={(e) => setAlertTimeStart(+e.target.value)}>
              {TIMES.map(t => (
                <option key={t.minutes} value={t.minutes}>{t.label}</option>
              ))}
            </select>
            <span className="to-label">to</span>
            <select value={alertTimeEnd} onChange={(e) => setAlertTimeEnd(+e.target.value)}>
              {TIMES.map(t => (
                <option key={t.minutes} value={t.minutes}>{t.label}</option>
              ))}
            </select>
            <select value={alertMinSpots} onChange={(e) => setAlertMinSpots(+e.target.value)}>
              {[1, 2, 3, 4].map(n => (
                <option key={n} value={n}>{n === 4 ? '4 spots' : `${n}+ spots`}</option>
              ))}
            </select>
            <button onClick={createAlert}>Create Alert</button>
          </div>
          {alertStatus && <p className="alert-status">{alertStatus}</p>}
        </div>
      )}

      {loading ? (
        <p className="loading">Loading...</p>
      ) : teeTimes.length === 0 ? (
        <p className="no-times">No available tee times</p>
      ) : (
        <>
          <div className="tee-times">
            {teeTimes.map((t, i) => (
              <div key={i} className="tee-time" onClick={openBooking}>
                <div className="time">{t.time_display}</div>
                <div className="details">
                  <span className="course-type">{t.course_name.split(' ').slice(-2).join(' ')}</span>
                  <span className="spots">{t.spots_available} spots</span>
                </div>
              </div>
            ))}
          </div>
          <p className="booking-hint">Tap a time to book on Denver Golf</p>
        </>
      )}
    </div>
  )
}

export default App
