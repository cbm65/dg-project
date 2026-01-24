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

function App() {
  const [teeTimes, setTeeTimes] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCourse, setSelectedCourse] = useState(COURSES[3])
  const [date, setDate] = useState(new Date().toISOString().split('T')[0])

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
