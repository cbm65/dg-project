import { useState, useEffect } from 'react'
import './App.css'

const API_URL = import.meta.env.PROD 
  ? 'https://api.denvertts303.com' 
  : 'http://localhost:8000'

const COURSES = [
  { club_id: 3660, course_id: 4711, name: "City Park" },
  { club_id: 3691, course_id: 4756, name: "Evergreen" },
  { club_id: 3713, course_id: 4770, name: "Harvard Gulch" },
  { club_id: 3629, course_id: 20573, name: "Kennedy" },
  { club_id: 3755, course_id: 4827, name: "Overland Park" },
  { club_id: 3831, course_id: 4928, name: "Wellshire" },
  { club_id: 3833, course_id: 4932, name: "Willis Case" },
]

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
  const [teeTimes, setTeeTimes] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCourse, setSelectedCourse] = useState(COURSES[3])
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])
  
  // Alert form state
  const [showAlertForm, setShowAlertForm] = useState(false)
  const [alertPhone, setAlertPhone] = useState('')
  const [alertTimeStart, setAlertTimeStart] = useState(420)
  const [alertTimeEnd, setAlertTimeEnd] = useState(600)
  const [alertStatus, setAlertStatus] = useState('')

  const fetchTeeTimes = async () => {
    setLoading(true)
    try {
      const res = await fetch(
        `${API_URL}/api/tee-times/${selectedCourse.club_id}/${selectedCourse.course_id}/${date}`
      )
      const data = await res.json()
      setTeeTimes(data)
    } catch (err) {
      console.error(err)
    }
    setLoading(false)
  }

  const createAlert = async () => {
    if (!alertPhone) {
      setAlertStatus('Please enter your phone number')
      return
    }
    try {
      const res = await fetch(`${API_URL}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: alertPhone.startsWith('+') ? alertPhone : `+1${alertPhone.replace(/\D/g, '')}`,
          club_id: selectedCourse.club_id,
          course_name: selectedCourse.name,
          date: date,
          time_start: alertTimeStart,
          time_end: alertTimeEnd
        })
      })
      if (res.ok) {
        setAlertStatus('✓ Alert created! You\'ll get a text when times open up.')
        setTimeout(() => {
          setShowAlertForm(false)
          setAlertStatus('')
        }, 3000)
      } else {
        setAlertStatus('Error creating alert')
      }
    } catch (err) {
      setAlertStatus('Error creating alert')
    }
  }

  useEffect(() => {
    fetchTeeTimes()
  }, [selectedCourse, date])

  return (
    <div className="app">
      <h1>⛳ Denver Golf Tee Times</h1>
      
      <div className="controls">
        <select 
          value={selectedCourse.club_id} 
          onChange={(e) => setSelectedCourse(COURSES.find(c => c.club_id === +e.target.value))}
        >
          {COURSES.map(c => (
            <option key={c.club_id} value={c.club_id}>{c.name}</option>
          ))}
        </select>
        
        <input 
          type="date" 
          value={date} 
          onChange={(e) => setDate(e.target.value)} 
        />
        
        <button onClick={fetchTeeTimes}>Refresh</button>
      </div>

      <button 
        className="alert-toggle"
        onClick={() => setShowAlertForm(!showAlertForm)}
      >
        🔔 {showAlertForm ? 'Hide Alert Form' : 'Set Up Alert'}
      </button>

      {showAlertForm && (
        <div className="alert-form">
          <p>Get a text when tee times at <strong>{selectedCourse.name}</strong> on <strong>{date}</strong> become available:</p>
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
        <div className="tee-times">
          {teeTimes.map((t, i) => (
            <div key={i} className="tee-time">
              <div className="time">{t.time_display}</div>
              <div className="details">
                <span className="course-type">{t.course_name.split(' ').slice(-2).join(' ')}</span>
                <span>{t.spots_available} spots</span>
                <span>${t.price}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default App
